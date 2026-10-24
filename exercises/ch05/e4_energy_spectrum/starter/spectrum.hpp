// SPDX-License-Identifier: MIT
// Exercise 5.4 starter: histogramming energy codes.
#pragma once

#include <array>
#include <cstdint>
#include <span>

namespace ex {

// MDQ-P1 energy codes are 11 bits (0.5 keV per code): 2,048 bins.
inline constexpr std::size_t kBins = 2048;
using Spectrum = std::array<std::uint64_t, kBins>;

// Adds every code (masked to 11 bits) to `h`. Both must give identical results.
void fill_simple(std::span<const std::uint16_t> codes, Spectrum& h) noexcept;
void fill_split(std::span<const std::uint16_t> codes, Spectrum& h) noexcept;

}  // namespace ex
