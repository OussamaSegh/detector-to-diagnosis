// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "spectrum.hpp"

namespace {
ex::Spectrum reference(const std::vector<std::uint16_t>& v) {
  ex::Spectrum h{};
  for (const auto c : v) {
    ++h[c & (ex::kBins - 1)];
  }
  return h;
}
}  // namespace

TEST(Spectrum, BothMatchTheReferenceForEverySize) {
  std::mt19937 rng{1};
  std::uniform_int_distribution<int> d{0, 65535};
  for (std::size_t n : {0U, 1U, 2U, 3U, 4U, 5U, 7U, 8U, 9U, 1000U, 100'003U}) {
    std::vector<std::uint16_t> v(n);
    for (auto& c : v) {
      c = static_cast<std::uint16_t>(d(rng));  // includes codes above 2047: masked
    }
    const auto expected = reference(v);
    ex::Spectrum a{};
    ex::Spectrum b{};
    ex::fill_simple(v, a);
    ex::fill_split(v, b);
    EXPECT_EQ(a, expected) << "simple n=" << n;
    EXPECT_EQ(b, expected) << "split n=" << n;
  }
}

TEST(Spectrum, AccumulatesAcrossCalls) {
  const std::vector<std::uint16_t> v(1000, 1022);
  ex::Spectrum a{};
  ex::Spectrum b{};
  for (int i = 0; i < 3; ++i) {
    ex::fill_simple(v, a);
    ex::fill_split(v, b);
  }
  EXPECT_EQ(a[1022], 3000U);
  EXPECT_EQ(b[1022], 3000U);
}

TEST(Spectrum, CountsBeyondThirtyTwoBitsInTheTotal) {
  // Sub-histograms may use narrower counters, but the result must not wrap.
  ex::Spectrum h{};
  h[7] = (std::uint64_t{1} << 32) - 2;
  const std::vector<std::uint16_t> v(5, 7);
  ex::fill_split(v, h);
  EXPECT_EQ(h[7], (std::uint64_t{1} << 32) + 3);
}
