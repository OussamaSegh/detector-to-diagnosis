// SPDX-License-Identifier: MIT
#include "gray_code.hpp"

namespace gray {

std::uint32_t decode(std::uint32_t gray) noexcept {
  return gray;  // TODO
}

int bits_changed(std::uint32_t a, std::uint32_t b) noexcept {
  return a == b ? 0 : 1;  // TODO
}

std::uint32_t readable(std::uint32_t write_gray_synced, std::uint32_t read_binary,
                       unsigned depth_log2) noexcept {
  // TODO: decode, subtract, and keep depth_log2 + 1 bits.
  (void)depth_log2;
  return write_gray_synced - read_binary;
}

}  // namespace gray
