// SPDX-License-Identifier: MIT
#include "minidaq/control/udp_detector.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstring>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/flight_recorder.hpp"

namespace minidaq::control {

namespace {

std::string errno_text(int e) {
  return std::string{std::strerror(e)};  // NOLINT(concurrency-mt-unsafe): control-thread setup and fault text only
}

}  // namespace

Expected<std::unique_ptr<UdpDetector>, std::string> UdpDetector::open(const config::UdpSettings& s) {
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(s.port);
  if (inet_pton(AF_INET, s.address.c_str(), &addr.sin_addr) != 1) {
    return Unexpected{"udp: \"" + s.address + "\" is not an IPv4 address"};
  }
  const int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    return Unexpected{"udp: socket: " + errno_text(errno)};
  }
  // [snippet:rcvbuf]
  // The kernel caps SO_RCVBUF at net.core.rmem_max without an error, so the
  // granted size is read back and reported: a silently small buffer is the
  // most common cause of packet loss on a DAQ PC.
  const int want = static_cast<int>(std::min<std::size_t>(s.receive_buffer_bytes, 1U << 30));
  (void)::setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &want, sizeof want);
  int granted = 0;
  socklen_t len = sizeof granted;
  (void)::getsockopt(fd, SOL_SOCKET, SO_RCVBUF, &granted, &len);
  // [/snippet:rcvbuf]
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the sockets API takes a sockaddr*
  if (::bind(fd, reinterpret_cast<const sockaddr*>(&addr), sizeof addr) != 0) {
    const int e = errno;
    ::close(fd);
    return Unexpected{"udp: bind " + s.address + ":" + std::to_string(s.port) + ": " + errno_text(e)};
  }
  std::unique_ptr<UdpDetector> d{new UdpDetector(fd, s)};
  sockaddr_in bound{};
  socklen_t blen = sizeof bound;
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): as above
  if (::getsockname(fd, reinterpret_cast<sockaddr*>(&bound), &blen) == 0) {
    d->port_ = ntohs(bound.sin_port);
  }
  // Linux doubles the value it stores (the extra half is its own bookkeeping)
  // and reports the doubled value, so the buffer for data is granted / 2.
  d->receive_buffer_bytes_ = static_cast<std::size_t>(std::max(granted, 0)) / 2;
  const bool capped = d->receive_buffer_bytes_ < s.receive_buffer_bytes;
  char buf[200];  // NOLINT(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays): snprintf target
  const int n = std::snprintf(buf, sizeof buf, "UDP readout on %s:%u, receive buffer %zu B%s", s.address.c_str(),
                              static_cast<unsigned>(d->port_), d->receive_buffer_bytes_,
                              capped ? " (less than requested: raise net.core.rmem_max)" : "");
  d->description_ = n >= 0 ? buf : "UDP readout";
  return d;
}

UdpDetector::UdpDetector(int fd, const config::UdpSettings& s)
    : fd_{fd},
      tracker_{readout::TrackerConfig{s.reorder_window_packets, s.max_hold_us * 1000}},
      buffers_(batch_datagrams * (readout::max_packet_bytes + 1)),
      pending_((batch_datagrams + s.reorder_window_packets) * readout::max_words) {}

UdpDetector::~UdpDetector() { ::close(fd_); }

// [snippet:read]
std::size_t UdpDetector::read(std::span<std::uint64_t> out) {
  // Receive only when everything delivered before has been read: pending_
  // then has room for the worst case of one batch.
  if (pending_size_ == 0) {
    pending_head_ = 0;
    receive_batch();
  }
  const std::size_t n = std::min(out.size(), pending_size_);
  std::copy_n(pending_.begin() + static_cast<std::ptrdiff_t>(pending_head_), n, out.begin());
  pending_head_ += n;
  pending_size_ -= n;
  return n;
}
// [/snippet:read]

void UdpDetector::receive_batch() {
  std::array<mmsghdr, batch_datagrams> msgs{};
  std::array<iovec, batch_datagrams> iov{};
  const std::size_t slot = readout::max_packet_bytes + 1;
  for (std::size_t i = 0; i < batch_datagrams; ++i) {
    iov[i].iov_base = buffers_.data() + i * slot;
    iov[i].iov_len = slot;
    msgs[i].msg_hdr.msg_iov = &iov[i];
    msgs[i].msg_hdr.msg_iovlen = 1;
  }
  const int got = ::recvmmsg(fd_, msgs.data(), batch_datagrams, MSG_DONTWAIT, nullptr);
  const std::int64_t now = monotonic_ns();
  auto deliver = [this](const readout::PacketHeader& h, std::span<const std::byte> payload) {
    for (std::size_t i = 0; i < h.word_count; ++i) {
      pending_[pending_head_ + pending_size_++] = readout::payload_word(payload, i);
    }
    if ((h.flags & readout::flag_end_of_stream) != 0) {
      end_of_stream_.store(true, std::memory_order_release);
    }
  };
  if (got < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
      counters_.socket_errno.store(errno, std::memory_order_relaxed);
    }
    tracker_.expire(now, deliver);  // idle: give up on gaps that waited too long
  } else {
    ++receive_batches_;
    for (int i = 0; i < got; ++i) {
      const auto& m = msgs[static_cast<std::size_t>(i)];
      const std::size_t size = (m.msg_hdr.msg_flags & MSG_TRUNC) != 0 ? slot : m.msg_len;
      ++datagrams_;
      const auto bytes = std::span<const std::byte>(buffers_).subspan(static_cast<std::size_t>(i) * slot, size);
      if (auto p = readout::parse_packet(bytes); !p) {
        ++rejected_[static_cast<std::size_t>(p.error())];
      } else if (source_ && *source_ != p->header.source) {
        ++other_source_;  // a second link on this port: not ours to merge (Chapter 10)
      } else {
        source_ = p->header.source;
        tracker_.offer(*p, now, deliver);
        if ((p->header.flags & readout::flag_end_of_stream) != 0) {
          tracker_.flush(deliver);  // nothing will fill the gaps now
          tracker_.restart();       // a new run may start from any sequence number
        }
      }
    }
    tracker_.expire(now, deliver);
  }
  publish_counters();
}

void UdpDetector::publish_counters() noexcept {
  const auto& t = tracker_.stats();
  constexpr auto r = std::memory_order_relaxed;
  counters_.datagrams.store(datagrams_, r);
  for (std::size_t i = 0; i < rejected_.size(); ++i) {
    counters_.rejected[i].store(rejected_[i], r);
  }
  counters_.other_source.store(other_source_, r);
  counters_.received.store(t.received, r);
  counters_.delivered.store(t.delivered, r);
  counters_.reordered.store(t.reordered, r);
  counters_.lost.store(t.lost, r);
  counters_.stale.store(t.stale, r);
  counters_.resyncs.store(t.resyncs, r);
  counters_.words.store(t.words, r);
  counters_.receive_batches.store(receive_batches_, r);
  // Only changes reach the flight recorder: a lossy link adds an event per batch, not per call.
  if (t.lost > traced_lost_) {
    trace(TraceCode::link_gap, t.lost - traced_lost_, t.lost);
    traced_lost_ = t.lost;
  }
  if (t.resyncs > traced_resyncs_) {
    trace(TraceCode::link_resync, t.resyncs);
    traced_resyncs_ = t.resyncs;
  }
}

std::optional<std::string> UdpDetector::fault() const {
  if (const int e = counters_.socket_errno.load(std::memory_order_relaxed); e != 0) {
    return "udp receive failed: " + errno_text(e);
  }
  return std::nullopt;
}

std::vector<DetectorCounter> UdpDetector::counters() const {
  constexpr auto r = std::memory_order_relaxed;
  std::vector<DetectorCounter> c{
      {"datagrams", counters_.datagrams.load(r)},   {"packets_received", counters_.received.load(r)},
      {"packets_delivered", counters_.delivered.load(r)}, {"packets_reordered", counters_.reordered.load(r)},
      {"packets_lost", counters_.lost.load(r)},     {"packets_stale", counters_.stale.load(r)},
      {"sequence_resyncs", counters_.resyncs.load(r)}, {"words_delivered", counters_.words.load(r)},
      {"other_source", counters_.other_source.load(r)}, {"receive_batches", counters_.receive_batches.load(r)},
      {"receive_buffer_bytes", receive_buffer_bytes_},  // set before the run; never changes
  };
  for (std::size_t i = 0; i < readout::num_packet_errors; ++i) {
    c.push_back({"rejected_" + std::string{readout::to_string(static_cast<readout::PacketError>(i))},
                 counters_.rejected[i].load(r)});
  }
  return c;
}

}  // namespace minidaq::control
