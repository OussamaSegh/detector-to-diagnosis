// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 24.1.
#include <gtest/gtest.h>

#include <vector>

#include "handshake.hpp"

using namespace hs;

namespace {
constexpr Cycle idle{false, false, 0};
Cycle word(std::uint64_t d, bool ready) { return {true, ready, d}; }
}  // namespace

TEST(Handshake, CountsTransfersStallsAndIdleCycles) {
  // Three words: the first moves at once, the second waits two cycles, the third one.
  const std::vector<Cycle> t{word(1, true), idle,           word(2, false), word(2, false),
                             word(2, true), word(3, false), word(3, true),  idle};
  const Report r = check(t);
  EXPECT_EQ(r.transfers, 3U);
  EXPECT_EQ(r.stalls, 3U);
  EXPECT_EQ(r.idle, 2U);
  EXPECT_EQ(r.longest_stall, 2U);
  EXPECT_TRUE(r.violations.empty());
}

TEST(Handshake, ReadyWithoutValidMovesNothing) {
  const std::vector<Cycle> t{{false, true, 7}, {false, true, 8}, word(9, true)};
  const Report r = check(t);
  EXPECT_EQ(r.transfers, 1U);
  EXPECT_EQ(r.idle, 2U);
  EXPECT_TRUE(r.violations.empty()) << "data may change freely while valid is 0";
}

TEST(Handshake, BackToBackWordsAreNotAViolation) {
  // A new word in the cycle after a transfer is a new word, not changed data.
  const std::vector<Cycle> t{word(1, true), word(2, true), word(3, false), word(3, true)};
  const Report r = check(t);
  EXPECT_EQ(r.transfers, 3U);
  EXPECT_TRUE(r.violations.empty());
}

TEST(Handshake, FindsAValidDroppedBeforeItsTransfer) {
  const std::vector<Cycle> t{word(5, false), word(5, false), idle, word(6, true)};
  const Report r = check(t);
  ASSERT_EQ(r.violations.size(), 1U);
  EXPECT_EQ(r.violations[0], "cycle 2: valid dropped before the transfer");
  EXPECT_EQ(r.transfers, 1U) << "the word 5 was never taken: it is lost";
}

TEST(Handshake, FindsDataThatChangedWhileWaiting) {
  const std::vector<Cycle> t{word(5, false), word(6, false), word(6, true), word(7, false),
                             word(8, true)};
  const Report r = check(t);
  ASSERT_EQ(r.violations.size(), 2U);
  EXPECT_EQ(r.violations[0], "cycle 1: data changed while waiting");
  EXPECT_EQ(r.violations[1], "cycle 4: data changed while waiting");
}

TEST(Handshake, MeasuresTheLongestBackPressure) {
  std::vector<Cycle> t;
  for (int i = 0; i < 5; ++i) {
    t.push_back(word(1, false));
  }
  t.push_back(word(1, true));
  for (int i = 0; i < 9; ++i) {
    t.push_back(word(2, false));
  }
  t.push_back(word(2, true));
  const Report r = check(t);
  EXPECT_EQ(r.longest_stall, 9U);
  EXPECT_EQ(r.stalls, 14U);
  EXPECT_TRUE(r.violations.empty());
  EXPECT_EQ(check({}).transfers, 0U);
}
