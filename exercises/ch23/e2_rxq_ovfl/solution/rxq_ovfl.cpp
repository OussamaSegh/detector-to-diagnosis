// SPDX-License-Identifier: MIT
#include "rxq_ovfl.hpp"

#include <cstring>

namespace rxq {

std::optional<std::uint32_t> rxq_ovfl(const msghdr& m) noexcept {
  if ((m.msg_flags & MSG_CTRUNC) != 0) {
    return std::nullopt;  // the kernel had more to say than the buffer could hold
  }
  // NOLINTBEGIN(cppcoreguidelines-pro-type-reinterpret-cast,cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-const-cast)
  for (cmsghdr* c = CMSG_FIRSTHDR(&m); c != nullptr; c = CMSG_NXTHDR(const_cast<msghdr*>(&m), c)) {
    if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SO_RXQ_OVFL &&
        c->cmsg_len >= CMSG_LEN(sizeof(std::uint32_t))) {
      std::uint32_t v = 0;
      std::memcpy(&v, CMSG_DATA(c), sizeof v);  // CMSG_DATA need not be aligned for a uint32_t
      return v;
    }
  }
  // NOLINTEND(cppcoreguidelines-pro-type-reinterpret-cast,cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-const-cast)
  return std::nullopt;
}

void DropCounter::observe(std::uint32_t cumulative) noexcept {
  just_before_ = cumulative - last_;  // unsigned: modulo 2^32, so a wrap needs no special case
  total_ += just_before_;
  last_ = cumulative;
}

}  // namespace rxq
