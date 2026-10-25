// SPDX-License-Identifier: MIT
// MiniDAQ - little-endian field access on byte buffers (Chapters 9 and 12).
//
// Wire and file formats are defined byte by byte. These helpers read and
// write an unsigned integer one byte at a time, so they are independent of
// the host's byte order and of alignment; compilers turn them into a single
// load or store on little-endian hosts. The caller checks the bounds.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <type_traits>

namespace minidaq {

template <typename T>
  requires std::is_unsigned_v<T>
[[nodiscard]] constexpr T load_le(std::span<const std::byte> b, std::size_t at) noexcept {
  T v = 0;
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    v = static_cast<T>(v | (static_cast<T>(std::to_integer<std::uint8_t>(b[at + i])) << (8 * i)));
  }
  return v;
}

template <typename T>
  requires std::is_unsigned_v<T>
constexpr void store_le(std::span<std::byte> b, std::size_t at, T v) noexcept {
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    b[at + i] = static_cast<std::byte>((v >> (8 * i)) & 0xFFU);
  }
}

}  // namespace minidaq
