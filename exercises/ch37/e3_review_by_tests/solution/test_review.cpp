// SPDX-License-Identifier: MIT
// Exercise 37.3: a review of assisted::coincident (tests/subject.hpp) written from requirement
// SRS-EX-037, one test per clause, each with the values at its edge (solution).
#include <gtest/gtest.h>

#include <cstdint>

#include "subject.hpp"

namespace {
constexpr std::uint64_t P = assisted::kPeriod;
constexpr std::uint64_t W = 4'000;  // a 4 ns window
}  // namespace

TEST(Coincident, CloseSinglesAreCoincident) {
  EXPECT_TRUE(assisted::coincident(1'000'000, 1'002'000, W));
}

TEST(Coincident, DistantSinglesAreNot) {
  EXPECT_FALSE(assisted::coincident(1'000'000, 1'010'000, W));
}

// Clause 3: "at most the window", so the edge is inside and one picosecond more is outside.
TEST(Coincident, TheWindowsEdgeIsInside) {
  EXPECT_TRUE(assisted::coincident(10'000, 10'000 + W, W));
  EXPECT_FALSE(assisted::coincident(10'000, 10'000 + W + 1, W));
  EXPECT_TRUE(assisted::coincident(5, 5, 0));
}

// Clause 2: the shorter way around the circle, across the wrap in both directions.
TEST(Coincident, AcrossTheWrap) {
  EXPECT_TRUE(assisted::coincident(P - 1'000, 1'000, W));
  EXPECT_TRUE(assisted::coincident(1'000, P - 1'000, W));
  EXPECT_FALSE(assisted::coincident(P - 1, 0, 0));  // one picosecond apart
  EXPECT_TRUE(assisted::coincident(P - 1, 0, 1));
}

// Clause 2 again: the distance does not depend on the order of the arguments.
TEST(Coincident, TheOrderOfTheArgumentsDoesNotMatter) {
  EXPECT_TRUE(assisted::coincident(1'002'000, 1'000'000, W));
  EXPECT_FALSE(assisted::coincident(1'010'000, 1'000'000, W));
}

// Clause 1: a timestamp the counter cannot produce is never coincident, even if its low 40 bits
// would be.
TEST(Coincident, AnInvalidTimestampIsNeverCoincident) {
  EXPECT_FALSE(assisted::coincident(P + 1'000, 1'000, W));
  EXPECT_FALSE(assisted::coincident(1'000, P + 1'000, W));
  EXPECT_FALSE(assisted::coincident(~std::uint64_t{0}, P - 1, W));
}

// Clause 4: a window of half the period or more is refused, at the edge.
TEST(Coincident, AWindowOfHalfThePeriodIsRefused) {
  EXPECT_FALSE(assisted::coincident(0, 0, P / 2));
  EXPECT_TRUE(assisted::coincident(0, P / 2 - 1, P / 2 - 1));
}

// Clause 2 with distances that need more than 32 bits: 2^32 ps is 4.3 ms.
TEST(Coincident, DistancesUseAllFortyBits) {
  const std::uint64_t four_ms = std::uint64_t{1} << 32;
  EXPECT_FALSE(assisted::coincident(1'000, 1'000 + four_ms, W));
  EXPECT_FALSE(assisted::coincident(0, four_ms + 10, W));
}
