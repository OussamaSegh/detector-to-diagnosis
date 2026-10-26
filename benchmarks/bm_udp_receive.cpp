// SPDX-License-Identifier: MIT
// Chapter 23: the cost of taking datagrams out of a socket, by receive call and batch size.
//
// Each iteration fills a loopback socket with 128 datagrams (timing paused), then drains it
// (timed) with recv, one datagram per call, or with recvmmsg, up to `batch` per call. The time
// per datagram is the receiving thread's cost of the system calls and the copies; the kernel's
// work of queuing the datagrams is done before the timer starts. Arguments: batch size (1 means
// recv), datagram size in bytes (1,472: a standard MTU; 8,208: MDQ-R1's largest, a jumbo frame).
#include <arpa/inet.h>
#include <benchmark/benchmark.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstddef>
#include <vector>

namespace {

constexpr int datagrams_per_fill = 128;

struct Pair {
  int rx = -1;
  int tx = -1;
  sockaddr_in to{};
  Pair() {
    rx = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    tx = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    const int want = 8 << 20;  // capped at net.core.rmem_max; 128 jumbo datagrams need about 2 MiB
    (void)::setsockopt(rx, SOL_SOCKET, SO_RCVBUF, &want, sizeof want);
    to.sin_family = AF_INET;
    to.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the sockets API
    (void)::bind(rx, reinterpret_cast<const sockaddr*>(&to), sizeof to);
    socklen_t len = sizeof to;
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): as above
    (void)::getsockname(rx, reinterpret_cast<sockaddr*>(&to), &len);
  }
  ~Pair() {
    ::close(rx);
    ::close(tx);
  }
  Pair(const Pair&) = delete;
  Pair& operator=(const Pair&) = delete;
  Pair(Pair&&) = delete;
  Pair& operator=(Pair&&) = delete;
};

void BM_Drain(benchmark::State& state) {
  const auto batch = static_cast<std::size_t>(state.range(0));
  const auto size = static_cast<std::size_t>(state.range(1));
  const Pair p;
  std::vector<std::byte> payload(size, std::byte{0x5A});
  std::vector<std::byte> buffers(batch * size);
  std::vector<mmsghdr> msgs(batch);
  std::vector<iovec> iov(batch);
  std::size_t received = 0;
  for (auto _ : state) {
    state.PauseTiming();
    for (int i = 0; i < datagrams_per_fill; ++i) {
      // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the sockets API
      (void)::sendto(p.tx, payload.data(), size, 0, reinterpret_cast<const sockaddr*>(&p.to),
                     sizeof p.to);
    }
    state.ResumeTiming();
    int got_now = 0;
    while (got_now < datagrams_per_fill) {
      if (batch == 1) {
        if (::recv(p.rx, buffers.data(), size, MSG_DONTWAIT) < 0) {
          break;
        }
        ++got_now;
        continue;
      }
      for (std::size_t i = 0; i < batch; ++i) {
        iov[i] = {buffers.data() + i * size, size};
        msgs[i].msg_hdr = {};
        msgs[i].msg_hdr.msg_iov = &iov[i];
        msgs[i].msg_hdr.msg_iovlen = 1;
      }
      const int n =
          ::recvmmsg(p.rx, msgs.data(), static_cast<unsigned>(batch), MSG_DONTWAIT, nullptr);
      if (n <= 0) {
        break;
      }
      got_now += n;
    }
    if (got_now != datagrams_per_fill) {
      state.SkipWithError("datagrams were dropped: raise net.core.rmem_max");
      break;
    }
    received += static_cast<std::size_t>(got_now);
  }
  state.SetItemsProcessed(static_cast<std::int64_t>(received));
  state.SetBytesProcessed(static_cast<std::int64_t>(received * size));
}

BENCHMARK(BM_Drain)
    ->ArgNames({"batch", "bytes"})
    ->ArgsProduct({{1, 8, 32, 64}, {1472, 8208}})
    ->Unit(benchmark::kMicrosecond);

}  // namespace
