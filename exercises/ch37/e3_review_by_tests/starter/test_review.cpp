// SPDX-License-Identifier: MIT
// Exercise 37.3: review assisted::coincident (tests/subject.hpp) by testing it against
// requirement SRS-EX-037. These are the two tests the assistant wrote with the function.
#include <gtest/gtest.h>

#include "subject.hpp"

TEST(Coincident, CloseSinglesAreCoincident) {
  EXPECT_TRUE(assisted::coincident(1'000'000, 1'002'000, 4'000));
}

TEST(Coincident, DistantSinglesAreNot) {
  EXPECT_FALSE(assisted::coincident(1'000'000, 1'010'000, 4'000));
}

// TODO: the requirement, clause by clause: the window's edge, the wrap of the counter, the order
// of the arguments, invalid timestamps, an invalid window, distances that need all 40 bits.
