// SPDX-License-Identifier: MIT
// Exercise 23.2: the kernel's drop count of a socket, from the ancillary data of each datagram.
#pragma once

#include <sys/socket.h>

#include <cstdint>
#include <optional>

namespace rxq {

// The SO_RXQ_OVFL value attached to a received datagram: how many datagrams the socket had dropped
// when this one was queued. Empty when the message carries no such control message (the option is
// off, or the control buffer was too small, which the kernel signals with MSG_CTRUNC).
[[nodiscard]] std::optional<std::uint32_t> rxq_ovfl(const msghdr& m) noexcept;

// Turns the kernel's cumulative 32-bit count into drops since the counter was created, across the
// count's wrap from 2^32 - 1 to 0.
class DropCounter {
 public:
  // The value attached to the next datagram. Values arrive in queue order, so a value smaller than
  // the last one has wrapped.
  void observe(std::uint32_t cumulative) noexcept;
  [[nodiscard]] std::uint64_t total() const noexcept { return total_; }
  // The drops between the previous datagram and the last one observed: the datagrams that were
  // lost right before it.
  [[nodiscard]] std::uint32_t just_before() const noexcept { return just_before_; }

 private:
  std::uint32_t last_ = 0;  // a socket's count starts at 0 when it is created
  std::uint64_t total_ = 0;
  std::uint32_t just_before_ = 0;
};

}  // namespace rxq
