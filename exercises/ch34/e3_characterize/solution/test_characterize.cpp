// SPDX-License-Identifier: MIT
// Exercise 34.3: characterization tests of legacy::corrected_rate (tests/subject.hpp). Each test
// is named after the behavior it pins; none of them says the behavior is right.
#include <gtest/gtest.h>

#include "subject.hpp"

using legacy::corrected_rate;

TEST(CorrectedRate, OneThousandCountsInOneSecond) {
  EXPECT_EQ(corrected_rate(1000, 1'000'000, 1'000'000), 1000);
}

TEST(CorrectedRate, HalfLiveDoublesTheRate) {
  EXPECT_EQ(corrected_rate(1000, 500'000, 1'000'000), 2000);
}

TEST(CorrectedRate, NoIntervalIsErrorMinusOneEvenAtZero) {
  EXPECT_EQ(corrected_rate(1000, 1'000'000, 0), -1);
  EXPECT_EQ(corrected_rate(1000, 1'000'000, -5), -1);
  EXPECT_EQ(corrected_rate(1000, 1, 1), 50'000'000);  // the smallest interval is not an error
}

TEST(CorrectedRate, ANegativeCountIsErrorMinusTwo) {
  EXPECT_EQ(corrected_rate(-1, 1'000'000, 1'000'000), -2);
  EXPECT_EQ(corrected_rate(0, 1'000'000, 1'000'000), 0);
}

TEST(CorrectedRate, ABlockDeadTheWholeIntervalShowsZeroNotAnError) {
  // Looks wrong (a dead block is indistinguishable from a quiet one); pinned, and reported.
  EXPECT_EQ(corrected_rate(1000, 0, 1'000'000), 0);
  EXPECT_EQ(corrected_rate(1000, -3, 1'000'000), 0);
}

TEST(CorrectedRate, ALiveTimeLongerThanTheIntervalIsCutToTheInterval) {
  EXPECT_EQ(corrected_rate(1000, 2'000'000, 1'000'000), 1000);
  EXPECT_EQ(corrected_rate(1000, 1'000'001, 1'000'000), 1000);
}

TEST(CorrectedRate, TheRateIsTruncatedNotRounded) {
  EXPECT_EQ(corrected_rate(2, 3'000'000, 3'000'000), 0);  // 0.67 per second shows 0
  EXPECT_EQ(corrected_rate(5, 3'000'000, 3'000'000), 1);  // 1.67 shows 1
}

TEST(CorrectedRate, CountsAreScaledBeforeTheDivision) {
  // 999 counts in 2 ms: 499,500 per second. Dividing first would give 0.
  EXPECT_EQ(corrected_rate(999, 2'000, 1'000'000), 499'500);
}

TEST(CorrectedRate, TheDisplayLimitIsFiftyMillionAndItIsReached) {
  EXPECT_EQ(corrected_rate(50'000'000, 1'000'000, 1'000'000), 50'000'000);
  EXPECT_EQ(corrected_rate(50'000'001, 1'000'000, 1'000'000), 50'000'000);
  EXPECT_EQ(corrected_rate(6'000'000, 1'000'000, 1'000'000), 6'000'000);
}
