// SPDX-License-Identifier: MIT
#include "split_counter.hpp"

namespace split {

std::optional<std::uint64_t> read_counter(Bus& bus, std::uint32_t lo_address,
                                          std::uint32_t hi_address, int attempts) {
  // High, low, high: if the high half did not change around the read of the low half, the low
  // half was read while the high half had that value, and the two belong together.
  for (int i = 0; i < attempts; ++i) {
    const auto hi1 = bus.read32(hi_address);
    const auto lo = hi1 ? bus.read32(lo_address) : std::nullopt;
    const auto hi2 = lo ? bus.read32(hi_address) : std::nullopt;
    if (!hi2) {
      return std::nullopt;
    }
    if (*hi1 == *hi2) {
      return (std::uint64_t{*hi1} << 32U) | *lo;
    }
  }
  return std::nullopt;
}

}  // namespace split
