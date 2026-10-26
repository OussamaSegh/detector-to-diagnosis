// SPDX-License-Identifier: MIT
// Exercise 23.4: receive datagrams in batches with recvmmsg, into buffers allocated once.
#pragma once

#include <sys/socket.h>

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace rx {

class BatchReceiver {
 public:
  // `fd` is a non-blocking UDP socket that the caller owns; `batch` datagrams of at most
  // `max_datagram` bytes are received per call. Every buffer is allocated here.
  BatchReceiver(int fd, std::size_t batch, std::size_t max_datagram);

  // Receives up to `batch` datagrams without waiting and returns how many; 0 when none is
  // queued or the receive failed (then error() says why). The datagrams of the previous call are
  // overwritten.
  std::size_t receive();

  // The i-th datagram of the last call, at most max_datagram bytes.
  [[nodiscard]] std::span<const std::byte> datagram(std::size_t i) const;
  // Whether the i-th datagram was longer than max_datagram (and so is incomplete).
  [[nodiscard]] bool truncated(std::size_t i) const;
  // The SO_RXQ_OVFL value of the i-th datagram, or 0 when the option is off.
  [[nodiscard]] std::uint32_t drops_when_queued(std::size_t i) const;

  [[nodiscard]] std::uint64_t calls() const noexcept { return calls_; }
  [[nodiscard]] int error() const noexcept { return error_; }  // errno, other than EAGAIN

 private:
  static constexpr std::size_t control_bytes = 64;
  int fd_;
  std::size_t batch_;
  std::size_t slot_;  // max_datagram + 1: one byte more shows a datagram that is too long
  std::vector<std::byte> data_;
  std::vector<std::byte> control_;
  std::vector<iovec> iov_;
  std::vector<mmsghdr> msgs_;
  std::size_t received_ = 0;
  std::uint64_t calls_ = 0;
  int error_ = 0;
};

}  // namespace rx
