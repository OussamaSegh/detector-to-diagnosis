// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <stdexcept>
#include <vector>

#include "speedup.hpp"

namespace {
std::vector<double> noisy(double center, double spread, int n, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::normal_distribution<double> d{center, spread};
  std::vector<double> v;
  for (int i = 0; i < n; ++i) {
    v.push_back(std::max(1e-3, d(rng)));
  }
  return v;
}
}  // namespace

TEST(SpeedupCi, ClearTwoTimesSpeedup) {
  const auto before = noisy(100.0, 3.0, 10, 1);
  const auto after = noisy(50.0, 1.5, 10, 2);
  const auto ci = ex::speedup_ci(before, after);
  EXPECT_NEAR(ci.estimate, 2.0, 0.1);
  EXPECT_GT(ci.low, 1.85);
  EXPECT_LT(ci.high, 2.15);
  EXPECT_LE(ci.low, ci.estimate);
  EXPECT_GE(ci.high, ci.estimate);
}

TEST(SpeedupCi, NoChangeIncludesOne) {
  const auto before = noisy(100.0, 10.0, 8, 3);
  const auto after = noisy(100.0, 10.0, 8, 4);
  const auto ci = ex::speedup_ci(before, after);
  EXPECT_LT(ci.low, 1.0);
  EXPECT_GT(ci.high, 1.0);
}

TEST(SpeedupCi, NoisyFivePercentIsNotProven) {
  // A 5% "speedup" measured with 20% noise and 5 repetitions: the interval is wide.
  const auto before = noisy(100.0, 20.0, 5, 5);
  const auto after = noisy(95.0, 19.0, 5, 6);
  const auto ci = ex::speedup_ci(before, after);
  EXPECT_LT(ci.low, 1.0);
  EXPECT_GT(ci.high - ci.low, 0.2);
}

TEST(SpeedupCi, DeterministicForASeedAndWiderAtHigherConfidence) {
  const auto before = noisy(100.0, 5.0, 9, 7);
  const auto after = noisy(80.0, 5.0, 9, 8);
  const auto a = ex::speedup_ci(before, after, 0.95, 5000, 42);
  const auto b = ex::speedup_ci(before, after, 0.95, 5000, 42);
  EXPECT_NEAR(a.estimate, 1.25, 0.1);
  EXPECT_LT(a.low, a.high);
  EXPECT_EQ(a.low, b.low);
  EXPECT_EQ(a.high, b.high);
  const auto wide = ex::speedup_ci(before, after, 0.99, 5000, 42);
  EXPECT_LE(wide.low, a.low);
  EXPECT_GE(wide.high, a.high);
}

TEST(SpeedupCi, RejectsBadInput) {
  const std::vector<double> ok{1.0, 2.0, 3.0};
  const std::vector<double> two{1.0, 2.0};
  const std::vector<double> zero{1.0, 0.0, 3.0};
  EXPECT_THROW((void)ex::speedup_ci(two, ok), std::invalid_argument);
  EXPECT_THROW((void)ex::speedup_ci(ok, zero), std::invalid_argument);
  EXPECT_THROW((void)ex::speedup_ci(ok, ok, 1.0), std::invalid_argument);
  EXPECT_THROW((void)ex::speedup_ci(ok, ok, 0.95, 10), std::invalid_argument);
}
