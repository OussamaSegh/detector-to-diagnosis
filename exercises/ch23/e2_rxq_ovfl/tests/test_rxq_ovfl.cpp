// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 23.2: control messages built by hand, then a real socket.
#include <arpa/inet.h>
#include <gtest/gtest.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <array>
#include <cstring>
#include <vector>

#include "rxq_ovfl.hpp"

namespace {

// A message whose control buffer holds one control message of the given level and type.
struct Built {
  alignas(cmsghdr) std::array<unsigned char, CMSG_SPACE(sizeof(std::uint32_t)) + 64> control{};
  msghdr m{};
  Built(int level, int type, std::uint32_t value) {
    m.msg_control = control.data();
    m.msg_controllen = CMSG_SPACE(sizeof value);
    cmsghdr* c = CMSG_FIRSTHDR(&m);
    c->cmsg_level = level;
    c->cmsg_type = type;
    c->cmsg_len = CMSG_LEN(sizeof value);
    std::memcpy(CMSG_DATA(c), &value, sizeof value);
  }
};

}  // namespace

TEST(RxqOvfl, ReadsTheValueOfItsControlMessage) {
  const Built b{SOL_SOCKET, SO_RXQ_OVFL, 117};
  ASSERT_TRUE(rxq::rxq_ovfl(b.m));
  EXPECT_EQ(*rxq::rxq_ovfl(b.m), 117U);
}

TEST(RxqOvfl, IgnoresOtherControlMessagesAndATruncatedBuffer) {
  const Built other{SOL_SOCKET, SO_TIMESTAMP, 117};
  EXPECT_FALSE(rxq::rxq_ovfl(other.m));
  const Built ip{IPPROTO_IP, SO_RXQ_OVFL, 117};
  EXPECT_FALSE(rxq::rxq_ovfl(ip.m)) << "the level matters, not only the type";
  Built cut{SOL_SOCKET, SO_RXQ_OVFL, 117};
  cut.m.msg_flags = MSG_CTRUNC;
  EXPECT_FALSE(rxq::rxq_ovfl(cut.m));
  msghdr none{};
  EXPECT_FALSE(rxq::rxq_ovfl(none));
}

TEST(DropCounter, CountsTheDropsBetweenDatagrams) {
  rxq::DropCounter d;
  d.observe(0);
  EXPECT_EQ(d.total(), 0U);
  d.observe(5);
  EXPECT_EQ(d.just_before(), 5U);
  d.observe(5);
  EXPECT_EQ(d.just_before(), 0U);
  d.observe(12);
  EXPECT_EQ(d.just_before(), 7U);
  EXPECT_EQ(d.total(), 12U);
}

TEST(DropCounter, FollowsTheCountAcrossItsWrap) {
  rxq::DropCounter d;
  d.observe(0xFFFF'FFF0U);
  d.observe(0x10U);
  EXPECT_EQ(d.just_before(), 0x20U);
  EXPECT_EQ(d.total(), 0x1'0000'0010ULL);
}

TEST(RxqOvfl, ARealSocketReportsItsDropsWithTheNextDatagram) {
  const int rx = ::socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
  const int tx = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  ASSERT_GE(rx, 0);
  const int on = 1;
  const int tiny = 1;  // the kernel's minimum: room for a datagram or two
  ASSERT_EQ(::setsockopt(rx, SOL_SOCKET, SO_RXQ_OVFL, &on, sizeof on), 0);
  ASSERT_EQ(::setsockopt(rx, SOL_SOCKET, SO_RCVBUF, &tiny, sizeof tiny), 0);
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
  ASSERT_EQ(::bind(rx, reinterpret_cast<const sockaddr*>(&a), sizeof a), 0);
  socklen_t len = sizeof a;
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
  ASSERT_EQ(::getsockname(rx, reinterpret_cast<sockaddr*>(&a), &len), 0);
  const std::vector<char> payload(1400, 'x');
  const auto send = [&] {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast)
    return ::sendto(tx, payload.data(), payload.size(), 0, reinterpret_cast<const sockaddr*>(&a), sizeof a);
  };
  for (int i = 0; i < 20; ++i) {
    ASSERT_EQ(send(), static_cast<ssize_t>(payload.size()));
  }
  rxq::DropCounter drops;
  std::vector<char> buf(2048);
  alignas(cmsghdr) std::array<unsigned char, 64> control{};
  const auto receive_all = [&] {
    int n = 0;
    for (;;) {
      iovec iov{buf.data(), buf.size()};
      msghdr m{};
      m.msg_iov = &iov;
      m.msg_iovlen = 1;
      m.msg_control = control.data();
      m.msg_controllen = control.size();
      if (::recvmsg(rx, &m, 0) < 0) {
        return n;
      }
      ++n;
      if (const auto v = rxq::rxq_ovfl(m)) {
        drops.observe(*v);
      }
    }
  };
  const int first = receive_all();
  ASSERT_GT(first, 0);
  ASSERT_LT(first, 20) << "the buffer should have overflowed";
  EXPECT_EQ(drops.total(), 0U) << "the datagrams that arrived were queued before the drops";
  ASSERT_EQ(send(), static_cast<ssize_t>(payload.size()));
  EXPECT_EQ(receive_all(), 1);
  EXPECT_EQ(drops.total(), static_cast<std::uint64_t>(20 - first));
  EXPECT_EQ(drops.just_before(), static_cast<std::uint32_t>(20 - first));
  ::close(rx);
  ::close(tx);
}
