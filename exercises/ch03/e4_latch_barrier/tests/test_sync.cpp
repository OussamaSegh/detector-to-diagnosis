// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "sync.hpp"

TEST(Latch, EveryoneStartsAfterEveryoneArrived) {
  for (int rep = 0; rep < 50; ++rep) {
    const auto seen = ex::start_together(6);
    ASSERT_EQ(seen.size(), 6U);
    for (const int v : seen) {
      ASSERT_EQ(v, 6) << "a worker started before all had arrived (rep " << rep << ")";
    }
  }
}

TEST(Barrier, PhaseTotalsAreExact) {
  constexpr int phases = 200;
  constexpr int workers = 4;
  std::vector<std::vector<std::int64_t>> values(phases, std::vector<std::int64_t>(workers));
  std::vector<std::int64_t> want(phases, 0);
  for (int p = 0; p < phases; ++p) {
    for (int w = 0; w < workers; ++w) {
      values[static_cast<std::size_t>(p)][static_cast<std::size_t>(w)] = (p + 1) * 10 + w;
      want[static_cast<std::size_t>(p)] += (p + 1) * 10 + w;
    }
  }
  const auto r = ex::phased_sums(values);
  EXPECT_EQ(r.totals, want);
  EXPECT_EQ(r.completions, phases);
}
