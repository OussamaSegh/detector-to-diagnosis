// SPDX-License-Identifier: MIT
// Exercise 34.3: characterization tests of legacy::corrected_rate (tests/subject.hpp).
#include <gtest/gtest.h>

#include "subject.hpp"

TEST(CorrectedRate, OneThousandCountsInOneSecond) {
  EXPECT_EQ(legacy::corrected_rate(1000, 1'000'000, 1'000'000), 1000);
}

TEST(CorrectedRate, HalfLiveDoublesTheRate) {
  EXPECT_EQ(legacy::corrected_rate(1000, 500'000, 1'000'000), 2000);
}

// TODO: the error codes, the dead block, the clamp of the live time, the truncation, the display
// limit. Each comparison in the code is a boundary to test on both sides.
