#include <gtest/gtest.h>

#include <optional>
#include <random>
#include <vector>

#include "singles.hpp"

using ex::Single;

namespace {
std::vector<Single> sample() {
  return {{300, 7, 511.0F}, {100, 2, 340.0F}, {200, 7, 650.0F}, {100, 1, 505.0F}, {400, 3, 90.0F}};
}
}  // namespace

TEST(Algorithms, CountInWindowIsInclusive) {
  const auto s = sample();
  EXPECT_EQ(ex::count_in_window(s, 435.0F, 585.0F), 2U);
  EXPECT_EQ(ex::count_in_window(s, 511.0F, 511.0F), 1U);
  EXPECT_EQ(ex::count_in_window({}, 0.0F, 1000.0F), 0U);
}

TEST(Algorithms, HighestEnergy) {
  const auto s = sample();
  const auto top = ex::highest_energy(s);
  ASSERT_TRUE(top.has_value());
  EXPECT_EQ(top->time_ps, 200);
  EXPECT_FALSE(ex::highest_energy({}).has_value());
}

TEST(Algorithms, MeanEnergy) {
  const auto s = sample();
  const auto m = ex::mean_energy(s);
  ASSERT_TRUE(m.has_value());
  EXPECT_NEAR(*m, (511.0 + 340.0 + 650.0 + 505.0 + 90.0) / 5.0, 1e-9);
  EXPECT_FALSE(ex::mean_energy({}).has_value());
}

TEST(Algorithms, SortByTimeThenCrystal) {
  auto s = sample();
  ex::sort_by_time(s);
  ASSERT_EQ(s.size(), 5U);
  EXPECT_EQ(s[0].crystal, 1U);  // time 100, crystal 1 before crystal 2
  EXPECT_EQ(s[1].crystal, 2U);
  EXPECT_EQ(s[2].time_ps, 200);
  EXPECT_EQ(s[4].time_ps, 400);
  EXPECT_TRUE(ex::is_time_ordered(s));
  EXPECT_FALSE(ex::is_time_ordered(sample()));
}

TEST(Algorithms, DropOutsideWindowKeepsOrder) {
  auto s = sample();
  ex::drop_outside_window(s, 435.0F, 585.0F);
  ASSERT_EQ(s.size(), 2U);
  EXPECT_EQ(s[0].time_ps, 300);
  EXPECT_EQ(s[1].time_ps, 100);
}

TEST(Algorithms, CountsPerCrystal) {
  const auto counts = ex::counts_per_crystal(sample());
  EXPECT_EQ(counts.size(), 4U);
  EXPECT_EQ(counts.at(7), 2U);
  EXPECT_EQ(counts.at(3), 1U);
  EXPECT_FALSE(counts.contains(99));
}

TEST(Algorithms, AgreeWithALoopOnRandomSingles) {
  std::mt19937 rng{20261127};
  std::uniform_int_distribution<std::int64_t> t{0, 1000};
  std::uniform_int_distribution<std::uint32_t> c{0, 63};
  std::uniform_real_distribution<float> e{0.0F, 800.0F};
  std::vector<Single> s(5000);
  for (auto& x : s) x = {t(rng), c(rng), e(rng)};
  std::size_t in = 0;
  for (const auto& x : s) in += (x.energy_kev >= 435.0F && x.energy_kev <= 585.0F) ? 1 : 0;
  EXPECT_EQ(ex::count_in_window(s, 435.0F, 585.0F), in);
  auto sorted = s;
  ex::sort_by_time(sorted);
  EXPECT_TRUE(ex::is_time_ordered(sorted));
  auto kept = s;
  ex::drop_outside_window(kept, 435.0F, 585.0F);
  EXPECT_EQ(kept.size(), in);
}
