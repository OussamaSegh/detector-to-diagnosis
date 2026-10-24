// SPDX-License-Identifier: MIT
// MiniDAQ - the "raw16" debug record and its parser (Chapter 1).
//
// raw16 is the simplest possible on-the-wire Single: 16 bytes, little-endian,
//   bytes 0..7   int64  time in picoseconds (>= 0)
//   bytes 8..11  uint32 crystal id (< ScannerGeometry::num_crystals)
//   bytes 12..15 float  energy in keV (finite, 0..2000)
// Chapter 2 replaces it with a packed 8-byte word; raw16 stays as a debug
// and test-vector format because it is easy to read in a hex dump.
#pragma once

#include <array>
#include <cstddef>
#include <span>
#include <string_view>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq {

enum class ParseError : std::uint8_t {
  truncated,
  negative_time,
  crystal_out_of_range,
  energy_not_finite,
  energy_out_of_range,
};

[[nodiscard]] std::string_view to_string(ParseError e) noexcept;

inline constexpr std::size_t raw16_size = 16;
inline constexpr float raw16_max_energy_kev = 2000.0F;

// Parses exactly one record from the front of `bytes`. Never reads past the
// span, never allocates, never throws.
[[nodiscard]] Expected<Single, ParseError> parse_single(std::span<const std::byte> bytes) noexcept;

// Inverse of parse_single, used by tests and the simulator.
[[nodiscard]] std::array<std::byte, raw16_size> serialize_raw16(const Single& s) noexcept;

}  // namespace minidaq
