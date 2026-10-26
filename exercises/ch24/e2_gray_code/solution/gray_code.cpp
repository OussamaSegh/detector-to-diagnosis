// SPDX-License-Identifier: MIT
#include "gray_code.hpp"

#include <bit>

namespace gray {

std::uint32_t decode(std::uint32_t gray) noexcept {
  // Each binary bit is the XOR of the Gray bits at and above it: fold the word onto itself.
  std::uint32_t b = gray;
  for (unsigned shift = 1; shift < 32; shift <<= 1U) {
    b ^= b >> shift;
  }
  return b;
}

int bits_changed(std::uint32_t a, std::uint32_t b) noexcept { return std::popcount(a ^ b); }

std::uint32_t readable(std::uint32_t write_gray_synced, std::uint32_t read_binary,
                       unsigned depth_log2) noexcept {
  const std::uint32_t mask = (std::uint32_t{2} << depth_log2) - 1U;  // depth_log2 + 1 bits
  return (decode(write_gray_synced) - read_binary) & mask;
}

}  // namespace gray
