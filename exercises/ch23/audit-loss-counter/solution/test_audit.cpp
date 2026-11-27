// SPDX-License-Identifier: MIT
// Exercise 23.5 (A): tests of the agent's loss counter, one per thing a network
// or a link does to the sequence numbers.
#include <gtest/gtest.h>

#include <cstdint>
#include <initializer_list>

#include "subject.hpp"

namespace {

ex235::LossStats after(std::initializer_list<std::uint32_t> seqs) {
  ex235::LossCounter c;
  for (const std::uint32_t s : seqs) {
    c.offer(s);
  }
  return c.stats();
}

TEST(Audit, PacketsInOrderLoseNothing) {
  const auto s = after({7, 8, 9, 10});
  EXPECT_EQ(s.received, 4U);
  EXPECT_EQ(s.lost, 0U);
  EXPECT_EQ(s.reordered + s.stale + s.resyncs, 0U);
}

TEST(Audit, AGapIsCountedAsLost) { EXPECT_EQ(after({1, 2, 6}).lost, 3U); }

TEST(Audit, NumberingThatWrapsIsNotALoss) {
  const auto s = after({0xFFFFFFFE, 0xFFFFFFFF, 0, 1});
  EXPECT_EQ(s.lost, 0U);
  EXPECT_EQ(s.resyncs, 0U);
}

TEST(Audit, ALatePacketFillsItsGapAndIsReordered) {
  const auto s = after({1, 3, 2});
  EXPECT_EQ(s.lost, 0U);
  EXPECT_EQ(s.reordered, 1U);
  EXPECT_EQ(s.stale, 0U);
}

TEST(Audit, ACopyIsStaleOnly) {
  const auto s = after({1, 2, 2});
  EXPECT_EQ(s.stale, 1U);
  EXPECT_EQ(s.reordered, 0U);
}

// A packet both delayed and duplicated: its first copy filled the gap, the
// second arrives later still. It is a copy, not a reordered packet.
TEST(Audit, ALateCopyOfAPacketAlreadyReceivedIsStaleNotReordered) {
  const auto s = after({1, 3, 2, 4, 2});
  EXPECT_EQ(s.reordered, 1U);
  EXPECT_EQ(s.stale, 1U);
  EXPECT_EQ(s.lost, 0U);
  EXPECT_EQ(s.reordered + s.stale + s.lost, 2U) << "a packet is counted in one category";
}

TEST(Audit, AJumpLargerThanAnyNetworkMakesIsARestartNotALoss) {
  const auto s = after({100, 101, 100 + (std::uint32_t{1} << 25)});
  EXPECT_EQ(s.resyncs, 1U);
  EXPECT_EQ(s.lost, 0U);
}

// fuzz_packet's finding: serial arithmetic has no answer at a distance of 2^31.
// The packet after start + 1 is expected to be start + 2; this one is 2^31 past it.
TEST(Audit, AJumpOfExactlyTwoToThe31IsARestartNotTwoBillionLost) {
  for (const std::uint32_t start : {0U, 5U, 0x80000000U, 0xFFFFFFF0U}) {
    const auto s = after({start, start + 1, start + 2 + 0x80000000U});
    EXPECT_EQ(s.lost, 0U) << start;
    EXPECT_EQ(s.resyncs, 1U) << start;
  }
}

TEST(Audit, CountingGoesOnAfterARestart) {
  const auto s = after({10, 11, 0x80000000U + 11, 0x80000000U + 12, 0x80000000U + 14});
  EXPECT_EQ(s.resyncs, 1U);
  EXPECT_EQ(s.lost, 1U);
}

}  // namespace
