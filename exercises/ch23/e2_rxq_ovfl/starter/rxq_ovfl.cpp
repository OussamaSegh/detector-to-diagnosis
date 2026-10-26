// SPDX-License-Identifier: MIT
#include "rxq_ovfl.hpp"

namespace rxq {

std::optional<std::uint32_t> rxq_ovfl(const msghdr& m) noexcept {
  // TODO: walk the control messages with CMSG_FIRSTHDR and CMSG_NXTHDR, find SOL_SOCKET /
  // SO_RXQ_OVFL, and copy its 32-bit value out of CMSG_DATA. What does MSG_CTRUNC mean for you?
  (void)m;
  return std::nullopt;
}

void DropCounter::observe(std::uint32_t cumulative) noexcept {
  // TODO: the drops since the previous value, and their running total. The count is 32-bit.
  (void)cumulative;
}

}  // namespace rxq
