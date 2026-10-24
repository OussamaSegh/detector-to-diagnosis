// SPDX-License-Identifier: MIT
// Exercise 5.4 starter.
#include "spectrum.hpp"

namespace ex {

void fill_simple(std::span<const std::uint16_t> codes, Spectrum& h) noexcept {
  // TODO: one increment per code.
  (void)codes, (void)h;
}

void fill_split(std::span<const std::uint16_t> codes, Spectrum& h) noexcept {
  // TODO: four sub-histograms, merged at the end. Mind the counter width.
  (void)codes, (void)h;
}

}  // namespace ex
