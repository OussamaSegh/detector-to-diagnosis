// SPDX-License-Identifier: MIT
// Count-rate figures of merit (Chapter 11).
#include <gtest/gtest.h>

#include "minidaq/processing/count_rates.hpp"

using namespace minidaq;

TEST(CountRates, NecrAndScatterFraction) {
  // REQ: SRS-CNT-001
  constexpr CountRates r{.trues = 100.0, .scatters = 50.0, .randoms = 25.0};
  EXPECT_DOUBLE_EQ(r.prompts(), 175.0);
  EXPECT_DOUBLE_EQ(r.scatter_fraction(), 50.0 / 150.0);
  EXPECT_DOUBLE_EQ(r.necr(1.0), 10'000.0 / 175.0);
  EXPECT_DOUBLE_EQ(r.necr(2.0), 10'000.0 / 200.0);
  static_assert(CountRates{.trues = 4.0}.necr(2.0) == 4.0, "trues only: NECR equals the trues rate");
  EXPECT_DOUBLE_EQ(CountRates{}.necr(1.0), 0.0);
  EXPECT_DOUBLE_EQ(CountRates{}.scatter_fraction(), 0.0);
}
