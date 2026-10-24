// SPDX-License-Identifier: MIT
// Exercise 5.4 solution.
#include "spectrum.hpp"

namespace ex {

void fill_simple(std::span<const std::uint16_t> codes, Spectrum& h) noexcept {
  for (const std::uint16_t c : codes) {
    ++h[c & (kBins - 1)];
  }
}

// [snippet:split]
// Four sub-histograms, one per position modulo 4. When the same bin comes up
// several times in a row (a peaked spectrum), consecutive increments of one
// counter form a chain: each load waits for the previous store. Spreading
// neighbours over four arrays breaks the chain into four independent ones.
void fill_split(std::span<const std::uint16_t> codes, Spectrum& h) noexcept {
  alignas(64) static thread_local std::array<std::array<std::uint32_t, kBins>, 4> sub{};
  for (auto& s : sub) {
    s.fill(0);
  }
  std::size_t i = 0;
  const std::size_t n = codes.size();
  for (; i + 4 <= n; i += 4) {
    ++sub[0][codes[i] & (kBins - 1)];
    ++sub[1][codes[i + 1] & (kBins - 1)];
    ++sub[2][codes[i + 2] & (kBins - 1)];
    ++sub[3][codes[i + 3] & (kBins - 1)];
  }
  for (; i < n; ++i) {
    ++sub[0][codes[i] & (kBins - 1)];
  }
  for (std::size_t b = 0; b < kBins; ++b) {
    h[b] += std::uint64_t{sub[0][b]} + sub[1][b] + sub[2][b] + sub[3][b];
  }
}
// [/snippet:split]

}  // namespace ex
