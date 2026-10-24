// SPDX-License-Identifier: MIT
// MiniDAQ - byte order helpers (Chapters 1 and 2).
//
// std::byteswap is C++23; this header gives the same operation in C++20 and
// uses the standard one when the library provides it.
#pragma once

#include <bit>
#include <concepts>
#include <cstdint>
#include <version>

namespace minidaq {

template <std::integral T>
[[nodiscard]] constexpr T byteswap(T v) noexcept {
#if defined(__cpp_lib_byteswap)
  return std::byteswap(v);
#else
  if constexpr (sizeof(T) == 1) {
    return v;
  } else if constexpr (sizeof(T) == 2) {
    return static_cast<T>(__builtin_bswap16(static_cast<std::uint16_t>(v)));
  } else if constexpr (sizeof(T) == 4) {
    return static_cast<T>(__builtin_bswap32(static_cast<std::uint32_t>(v)));
  } else {
    static_assert(sizeof(T) == 8);
    return static_cast<T>(__builtin_bswap64(static_cast<std::uint64_t>(v)));
  }
#endif
}

// Convert between host order and little-endian (the MiniDAQ wire order).
template <std::integral T>
[[nodiscard]] constexpr T to_little_endian(T v) noexcept {
  if constexpr (std::endian::native == std::endian::little) {
    return v;
  } else {
    return byteswap(v);
  }
}
template <std::integral T>
[[nodiscard]] constexpr T from_little_endian(T v) noexcept {
  return to_little_endian(v);
}

}  // namespace minidaq
