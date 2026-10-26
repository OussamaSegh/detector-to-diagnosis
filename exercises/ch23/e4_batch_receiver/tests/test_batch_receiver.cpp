// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 23.4, over the loopback interface.
#include <arpa/inet.h>
#include <gtest/gtest.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "batch_receiver.hpp"

namespace {

// A receiving and a sending socket on 127.0.0.1, closed at the end.
class Loopback {
 public:
  explicit Loopback(int receive_buffer = 1 << 20) {
    rx_ = ::socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    tx_ = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    (void)::setsockopt(rx_, SOL_SOCKET, SO_RCVBUF, &receive_buffer, sizeof receive_buffer);
    to_.sin_family = AF_INET;
    to_.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    (void)::bind(rx_, reinterpret_cast<const sockaddr*>(&to_), sizeof to_);
    socklen_t len = sizeof to_;
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    (void)::getsockname(rx_, reinterpret_cast<sockaddr*>(&to_), &len);
  }
  ~Loopback() {
    ::close(rx_);
    ::close(tx_);
  }
  Loopback(const Loopback&) = delete;
  Loopback& operator=(const Loopback&) = delete;
  Loopback(Loopback&&) = delete;
  Loopback& operator=(Loopback&&) = delete;

  void send(std::size_t size, std::uint8_t fill) const {
    const std::vector<std::uint8_t> d(size, fill);
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    ASSERT_EQ(::sendto(tx_, d.data(), d.size(), 0, reinterpret_cast<const sockaddr*>(&to_), sizeof to_),
              static_cast<ssize_t>(size));
  }
  [[nodiscard]] int fd() const { return rx_; }

 private:
  int rx_ = -1;
  int tx_ = -1;
  sockaddr_in to_{};
};

}  // namespace

TEST(BatchReceiver, ReceivesQueuedDatagramsInBatches) {
  const Loopback link;
  for (int i = 0; i < 100; ++i) {
    link.send(100 + static_cast<std::size_t>(i), static_cast<std::uint8_t>(i));
  }
  rx::BatchReceiver r{link.fd(), 32, 1472};
  std::vector<std::size_t> per_call;
  int next = 0;
  while (const std::size_t n = r.receive()) {
    per_call.push_back(n);
    for (std::size_t i = 0; i < n; ++i, ++next) {
      const auto d = r.datagram(i);
      ASSERT_EQ(d.size(), 100U + static_cast<std::size_t>(next));
      EXPECT_EQ(d.front(), static_cast<std::byte>(next));
      EXPECT_EQ(d.back(), static_cast<std::byte>(next));
      EXPECT_FALSE(r.truncated(i));
    }
  }
  EXPECT_EQ(next, 100);
  EXPECT_EQ(per_call, (std::vector<std::size_t>{32, 32, 32, 4}));
  EXPECT_EQ(r.calls(), 5U) << "four with datagrams, one that found none";
  EXPECT_EQ(r.error(), 0) << "an empty socket is not an error";
}

TEST(BatchReceiver, ReusesItsBuffers) {
  const Loopback link;
  rx::BatchReceiver r{link.fd(), 8, 1472};
  link.send(10, 1);
  ASSERT_EQ(r.receive(), 1U);
  const std::byte* first = r.datagram(0).data();
  link.send(10, 2);
  ASSERT_EQ(r.receive(), 1U);
  EXPECT_EQ(r.datagram(0).data(), first) << "the same buffer, not a new allocation";
  EXPECT_EQ(r.datagram(0).front(), std::byte{2});
  EXPECT_THROW((void)r.datagram(1), std::out_of_range);
}

TEST(BatchReceiver, FlagsADatagramThatIsTooLong) {
  const Loopback link;
  rx::BatchReceiver r{link.fd(), 4, 1000};
  link.send(1000, 1);
  link.send(1001, 2);
  link.send(9000, 3);
  ASSERT_EQ(r.receive(), 3U);
  EXPECT_FALSE(r.truncated(0)) << "exactly the largest size";
  EXPECT_TRUE(r.truncated(1));
  EXPECT_TRUE(r.truncated(2));
  EXPECT_EQ(r.datagram(2).size(), 1000U) << "never more than the largest size";
}

TEST(BatchReceiver, ReportsTheKernelsDropCount) {
  const Loopback link{1};  // the smallest buffer the kernel allows
  const int on = 1;
  ASSERT_EQ(::setsockopt(link.fd(), SOL_SOCKET, SO_RXQ_OVFL, &on, sizeof on), 0);
  rx::BatchReceiver r{link.fd(), 64, 1472};
  for (int i = 0; i < 20; ++i) {
    link.send(1400, 1);
  }
  const std::size_t first = r.receive();
  ASSERT_GT(first, 0U);
  ASSERT_LT(first, 20U);
  EXPECT_EQ(r.drops_when_queued(first - 1), 0U);
  link.send(1400, 2);
  ASSERT_EQ(r.receive(), 1U);
  EXPECT_EQ(r.drops_when_queued(0), 20U - first);
}

TEST(BatchReceiver, KeepsTheErrorOfAFailedReceive) {
  rx::BatchReceiver r{-1, 4, 100};
  EXPECT_EQ(r.receive(), 0U);
  EXPECT_EQ(r.error(), EBADF);
  EXPECT_THROW(rx::BatchReceiver(0, 0, 100), std::invalid_argument);
}
