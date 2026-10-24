#include <gtest/gtest.h>

#include "budget.hpp"

TEST(StreamBudget, ThirtyMillionSingles) {
  const auto b8 = ex::stream_budget(30e6, 8);
  EXPECT_DOUBLE_EQ(b8.bytes_per_s, 240e6);
  EXPECT_NEAR(b8.gib_per_s, 0.2235, 1e-4);
  EXPECT_DOUBLE_EQ(b8.gbit_per_s, 1.92);
  EXPECT_EQ(b8.records_per_cache_line, 8U);

  const auto b12 = ex::stream_budget(30e6, 12);
  EXPECT_DOUBLE_EQ(b12.bytes_per_s, 360e6);
  EXPECT_DOUBLE_EQ(b12.gbit_per_s, 2.88);
  EXPECT_EQ(b12.records_per_cache_line, 5U);  // 5 whole records; the 6th would straddle

  const auto b16 = ex::stream_budget(30e6, 16);
  EXPECT_DOUBLE_EQ(b16.bytes_per_s, 480e6);
  EXPECT_DOUBLE_EQ(b16.gbit_per_s, 3.84);
  EXPECT_EQ(b16.records_per_cache_line, 4U);
}

TEST(StreamBudget, RecordLargerThanALine) {
  EXPECT_EQ(ex::stream_budget(1e6, 100).records_per_cache_line, 0U);
}
