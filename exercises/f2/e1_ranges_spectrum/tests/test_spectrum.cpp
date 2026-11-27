#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "spectrum.hpp"

using ex::Binning;
using ex::Single;

namespace {
std::vector<Single> random_singles(std::size_t n, unsigned seed) {
  std::mt19937 rng{seed};
  std::uniform_real_distribution<float> e{0.0F, 800.0F};
  std::uniform_int_distribution<std::uint32_t> c{0, 63};
  std::vector<Single> s(n);
  std::int64_t t = 0;
  for (auto& x : s) x = {t += 100, c(rng), e(rng)};
  return s;
}
}  // namespace

TEST(Spectrum, EnergiesInWindowKeepOrder) {
  const std::vector<Single> s{{1, 0, 100.0F}, {2, 1, 511.0F}, {3, 2, 450.0F}, {4, 3, 600.0F}};
  const std::vector<float> e = ex::energies_in_window(s, 435.0F, 585.0F);
  EXPECT_EQ(e, (std::vector<float>{511.0F, 450.0F}));
  EXPECT_TRUE(ex::energies_in_window({}, 0.0F, 1.0F).empty());
}

TEST(Spectrum, HistogramCountsEveryInRangeSingleOnce) {
  const Binning b{0.0F, 800.0F, 80};
  const auto s = random_singles(10000, 1);
  const auto h = ex::spectrum(s, b);
  ASSERT_EQ(h.size(), 80U);
  std::size_t total = 0;
  for (auto c : h) total += c;
  EXPECT_EQ(total, s.size());
}

TEST(Spectrum, HistogramMatchesALoop) {
  const Binning b{100.0F, 700.0F, 60};
  const auto s = random_singles(20000, 2);
  std::vector<std::size_t> ref(60, 0);
  for (const auto& x : s) {
    if (x.energy_kev < b.lo || x.energy_kev >= b.hi) continue;
    const auto i = static_cast<std::size_t>((x.energy_kev - b.lo) / (b.hi - b.lo) * 60.0F);
    ++ref[i < 60 ? i : 59];
  }
  EXPECT_EQ(ex::spectrum(s, b), ref);
}

TEST(Spectrum, EdgesBelongToTheUpperBin) {
  const Binning b{0.0F, 10.0F, 10};
  const std::vector<Single> s{{1, 0, 0.0F}, {2, 0, 1.0F}, {3, 0, 9.999F}, {4, 0, 10.0F}};
  const auto h = ex::spectrum(s, b);
  EXPECT_EQ(h[0], 1U);
  EXPECT_EQ(h[1], 1U);
  EXPECT_EQ(h[9], 1U);  // 10.0 is outside [lo, hi)
}

TEST(Spectrum, PhotopeakFraction) {
  const std::vector<Single> s{{1, 0, 511.0F}, {2, 0, 200.0F}, {3, 0, 500.0F}, {4, 0, 50.0F}};
  EXPECT_DOUBLE_EQ(ex::photopeak_fraction(s, 435.0F, 585.0F), 0.5);
  EXPECT_DOUBLE_EQ(ex::photopeak_fraction({}, 435.0F, 585.0F), 0.0);
}
