// SPDX-License-Identifier: MIT
#include "buffer_sizing.hpp"

namespace sizing {

std::size_t granted(std::size_t requested, std::size_t rmem_max) noexcept {
  // TODO
  (void)rmem_max;
  return requested;
}

std::size_t capacity(std::size_t granted, std::size_t charged_bytes) noexcept {
  // TODO: count against twice the granted size; the last datagram may cross the limit.
  (void)charged_bytes;
  return granted / 1472;
}

double longest_stall_s(std::size_t granted, const Link& link) noexcept {
  // TODO
  (void)granted;
  (void)link;
  return 0;
}

std::optional<std::size_t> request_for(double stall_s, const Link& link,
                                       std::size_t rmem_max) noexcept {
  // TODO: the smallest request whose capacity covers the datagrams of the stall.
  (void)stall_s;
  (void)link;
  (void)rmem_max;
  return std::nullopt;
}

}  // namespace sizing
