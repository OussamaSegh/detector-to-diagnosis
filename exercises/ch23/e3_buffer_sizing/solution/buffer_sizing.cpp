// SPDX-License-Identifier: MIT
#include "buffer_sizing.hpp"

#include <algorithm>
#include <cmath>

namespace sizing {

std::size_t granted(std::size_t requested, std::size_t rmem_max) noexcept {
  return std::min(requested, rmem_max);
}

std::size_t capacity(std::size_t granted, std::size_t charged_bytes) noexcept {
  if (charged_bytes == 0) {
    return 0;
  }
  // The charge is a measured average and the kernel's accounting is not byte-exact (it reserves
  // memory in pages), so the estimate rounds down: it may be one datagram short, never one over.
  return 2 * granted / charged_bytes;
}

double longest_stall_s(std::size_t granted, const Link& link) noexcept {
  if (link.datagrams_per_s <= 0) {
    return 0;
  }
  return static_cast<double>(capacity(granted, link.charged_bytes)) / link.datagrams_per_s;
}

std::optional<std::size_t> request_for(double stall_s, const Link& link,
                                       std::size_t rmem_max) noexcept {
  const double needed = std::ceil(stall_s * link.datagrams_per_s);
  if (!(needed >= 0) || link.charged_bytes == 0) {
    return std::nullopt;
  }
  // capacity(g) = floor(2g / c) >= n holds from g = ceil(n c / 2).
  const auto n = static_cast<std::size_t>(needed);
  const std::size_t request = (n * link.charged_bytes + 1) / 2;
  if (request > rmem_max) {
    return std::nullopt;
  }
  return request;
}

}  // namespace sizing
