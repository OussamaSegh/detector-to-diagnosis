// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <vector>

#include "randoms.hpp"

TEST(Randoms, Formula) {
  EXPECT_DOUBLE_EQ(ex83::expected_randoms_per_s(1e6, 1e6, 4e-9), 8000.0);
  EXPECT_DOUBLE_EQ(ex83::expected_randoms_per_s(2e6, 1e6, 4e-9), 16000.0);
}

TEST(Randoms, CountsHandMadeStreams) {
  const std::vector<std::int64_t> a{1000, 5000, 9000};
  const std::vector<std::int64_t> b{0, 1000, 2000, 3001, 4000, 8999, 20000};
  // tau = 1000: 1000 pairs with 0, 1000, 2000; 5000 with 4000; 9000 with 8999.
  EXPECT_EQ(ex83::count_pairs_within(a, b, 1000), 5U);
  EXPECT_EQ(ex83::count_pairs_within(a, b, 0), 1U);
  EXPECT_EQ(ex83::count_pairs_within(b, a, 1000), 5U) << "symmetric";
  EXPECT_EQ(ex83::count_pairs_within({}, b, 1000), 0U);
  EXPECT_EQ(ex83::count_pairs_within(a, {}, 1000), 0U);
}

TEST(Randoms, MeasuredRateMatchesTheFormula) {
  const auto a = ex83::poisson_times_ps(1e6, 1.0, 1);
  const auto b = ex83::poisson_times_ps(1e6, 1.0, 2);
  const auto measured = static_cast<double>(ex83::count_pairs_within(a, b, 4000));
  const double expected = ex83::expected_randoms_per_s(static_cast<double>(a.size()), static_cast<double>(b.size()), 4e-9);
  EXPECT_NEAR(measured, expected, 4.0 * std::sqrt(expected));
}

TEST(Randoms, LinearTime) {
  const auto a = ex83::poisson_times_ps(1e6, 1.0, 3);
  const auto b = ex83::poisson_times_ps(1e6, 1.0, 4);
  const auto t0 = std::chrono::steady_clock::now();
  // A wide window: a quadratic counter visits about 2,000 b-singles per a-single.
  (void)ex83::count_pairs_within(a, b, 1'000'000'000);  // 1 ms
  EXPECT_LT(std::chrono::steady_clock::now() - t0, std::chrono::seconds{1});
}
