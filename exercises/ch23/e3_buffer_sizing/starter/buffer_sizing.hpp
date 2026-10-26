// SPDX-License-Identifier: MIT
// Exercise 23.3: how large a socket's receive buffer must be, and how long it lets the receiver
// stall.
#pragma once

#include <cstddef>
#include <optional>
#include <string>

namespace sizing {

struct Link {
  double datagrams_per_s = 0;      // the rate at the receiver, at the scanner's highest activity
  std::size_t charged_bytes = 0;   // what the kernel charges one datagram (measured, Chapter 23)
};

// What SO_RCVBUF grants for a request: the request, capped at net.core.rmem_max. (The kernel
// stores twice this value and reports the doubled value; the granted size is the half you asked
// for.)
[[nodiscard]] std::size_t granted(std::size_t requested, std::size_t rmem_max) noexcept;

// How many datagrams a buffer of `granted` bytes holds, at most one fewer than the kernel queues:
// the kernel queues a datagram while the charges of those already queued are below twice the
// granted size.
[[nodiscard]] std::size_t capacity(std::size_t granted, std::size_t charged_bytes) noexcept;

// The longest time the receiver may stop reading before the buffer overflows, in seconds.
[[nodiscard]] double longest_stall_s(std::size_t granted, const Link& link) noexcept;

// The smallest request that survives a stall of `stall_s` seconds; empty when rmem_max does not
// allow it.
[[nodiscard]] std::optional<std::size_t> request_for(double stall_s, const Link& link,
                                                     std::size_t rmem_max) noexcept;

}  // namespace sizing
