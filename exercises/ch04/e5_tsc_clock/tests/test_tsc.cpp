// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <thread>

#include "tsc_clock.hpp"

TEST(Tsc, CpuinfoFlagsNeedBothWholeWords) {
  EXPECT_TRUE(ex::tsc_is_invariant("processor\t: 0\nflags\t\t: fpu tsc constant_tsc rep_good nonstop_tsc cpuid\n"));
  EXPECT_FALSE(ex::tsc_is_invariant("flags\t\t: fpu tsc constant_tsc\n"));
  EXPECT_FALSE(ex::tsc_is_invariant("flags\t\t: fpu nonstop_tsc_x xconstant_tsc\n"));
  EXPECT_FALSE(ex::tsc_is_invariant("model name\t: constant_tsc nonstop_tsc\n"));  // not the flags line
  EXPECT_FALSE(ex::tsc_is_invariant(""));
}

TEST(Tsc, CalibratedRateIsPlausible) {
#if !defined(__x86_64__)
  GTEST_SKIP() << "no TSC on this architecture";
#endif
  ASSERT_NE(ex::read_tsc(), 0U);
  const auto clock = ex::TscClock::calibrate(std::chrono::milliseconds{50});
  EXPECT_GT(clock.ticks_per_us(), 500.0);
  EXPECT_LT(clock.ticks_per_us(), 10'000.0);
  RecordProperty("ticks_per_us", std::to_string(clock.ticks_per_us()));
}

TEST(Tsc, TracksMonotonicWithinAThousandth) {
#if !defined(__x86_64__)
  GTEST_SKIP() << "no TSC on this architecture";
#endif
  ASSERT_NE(ex::read_tsc(), 0U);
  const auto clock = ex::TscClock::calibrate(std::chrono::milliseconds{50});
  const std::int64_t m0 = ex::monotonic_ns();
  const std::int64_t t0 = clock.now_ns();
  EXPECT_LT(std::llabs(t0 - m0), 100'000) << "offset right after calibration";
  std::this_thread::sleep_for(std::chrono::milliseconds{100});  // sleep: minimum (the span both clocks measure)
  const std::int64_t m1 = ex::monotonic_ns();
  const std::int64_t t1 = clock.now_ns();
  const double elapsed_m = static_cast<double>(m1 - m0);
  const double elapsed_t = static_cast<double>(t1 - t0);
  EXPECT_NEAR(elapsed_t / elapsed_m, 1.0, 1e-3);
}
