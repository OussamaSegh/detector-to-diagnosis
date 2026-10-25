// SPDX-License-Identifier: MIT
// MiniDAQ - CRC-32 (Chapter 12).
//
// The CRC of IEEE 802.3, zlib and PNG: reflected polynomial 0xEDB88320,
// initial value and final XOR 0xFFFFFFFF. crc32("123456789") == 0xCBF43926,
// the check value every implementation of this CRC must reproduce.
//
// This CRC detects every error burst of up to 32 bits and every one or two
// flipped bits in any message up to 2^32 bits; three flipped bits are always
// detected only in messages up to 91,607 bits (Koopman, DSN 2002), so a 64 KiB
// block keeps the one- and two-bit guarantee but not the three-bit one. Any
// other corruption gets through with probability about 2^-32. It
// protects against accidents (a bad sector, a truncated write, a flipped bit
// in RAM), not against tampering: anyone who changes the data can recompute
// it. Integrity against tampering needs a signature (Chapter 17).
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace minidaq {

namespace detail {
// [snippet:tables]
// Eight tables for "slicing by 8": t[0] is the classic byte-at-a-time table,
// t[k][b] is the CRC of byte b followed by k zero bytes. Built at compile time.
inline constexpr std::array<std::array<std::uint32_t, 256>, 8> crc32_tables = [] {
  std::array<std::array<std::uint32_t, 256>, 8> t{};
  for (std::uint32_t b = 0; b < 256; ++b) {
    std::uint32_t c = b;
    for (int k = 0; k < 8; ++k) {
      c = (c & 1U) != 0 ? 0xEDB88320U ^ (c >> 1U) : c >> 1U;
    }
    t[0][b] = c;
  }
  for (std::size_t k = 1; k < 8; ++k) {
    for (std::uint32_t b = 0; b < 256; ++b) {
      const std::uint32_t prev = t[k - 1][b];
      t[k][b] = (prev >> 8U) ^ t[0][prev & 0xFFU];
    }
  }
  return t;
}();
// [/snippet:tables]
}  // namespace detail

// Continues a CRC over more bytes: crc32_update(crc32_update(0, a), b) equals
// the CRC of a followed by b. Start from 0.
[[nodiscard]] std::uint32_t crc32_update(std::uint32_t crc, std::span<const std::byte> data) noexcept;

[[nodiscard]] inline std::uint32_t crc32(std::span<const std::byte> data) noexcept { return crc32_update(0, data); }

// The textbook loop, one byte and one table lookup at a time: the reference
// the fast version is tested against, and the baseline of the benchmark.
[[nodiscard]] std::uint32_t crc32_bytewise(std::span<const std::byte> data) noexcept;

}  // namespace minidaq
