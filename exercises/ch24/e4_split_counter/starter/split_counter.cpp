// SPDX-License-Identifier: MIT
#include "split_counter.hpp"

namespace split {

std::optional<std::uint64_t> read_counter(Bus& bus, std::uint32_t lo_address,
                                          std::uint32_t hi_address, int attempts) {
  // TODO: this reads each half once, so a carry between the two reads tears the value. Read
  // high, low, high, and try again when the high half changed.
  (void)attempts;
  const auto lo = bus.read32(lo_address);
  const auto hi = bus.read32(hi_address);
  if (!lo || !hi) {
    return std::nullopt;
  }
  return (std::uint64_t{*hi} << 32U) | *lo;
}

}  // namespace split
