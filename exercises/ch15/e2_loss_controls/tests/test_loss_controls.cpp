// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 15.2. Each test names the risk control it
// verifies, as MiniDAQ's tests name requirements.
#include <gtest/gtest.h>

#include <cstdint>
#include <stdexcept>

#include "loss_controls.hpp"

using namespace ex152;

TEST(Assess, ACleanRunIsComplete) {
  // Control: acquisition invalidation
  const Verdict v = assess(Counters{});
  EXPECT_TRUE(v.complete);
  EXPECT_TRUE(v.losses.empty());
}

TEST(Assess, EveryLossCounterInvalidatesTheRun) {
  // Control: acquisition invalidation
  std::uint64_t Counters::*const fields[] = {
      &Counters::packets_lost, &Counters::sequence_resyncs, &Counters::packets_rejected, &Counters::words_invalid,
      &Counters::source_dropped, &Counters::sorter_out_of_order, &Counters::sink_invalid,
      &Counters::energies_clamped, &Counters::blocks_dropped};
  for (const auto f : fields) {
    Counters c;
    c.*f = 7;
    const Verdict v = assess(c);
    EXPECT_FALSE(v.complete);
    ASSERT_EQ(v.losses.size(), 1U);
    EXPECT_EQ(v.losses[0].count, 7U);
  }
}

TEST(Assess, LossesAreNamedInTheOrderOfTheCounters) {
  // Control: acquisition invalidation (the operator and the audit trail see which counters)
  Counters c;
  c.blocks_dropped = 1;
  c.packets_lost = 3;
  c.sorter_out_of_order = 2;
  const Verdict v = assess(c);
  const std::vector<Loss> expected{{"packets_lost", 3}, {"sorter_out_of_order", 2}, {"blocks_dropped", 1}};
  EXPECT_EQ(v.losses, expected);
}

TEST(Assess, AFaultInvalidatesTheRunWithoutALossCounter) {
  // Control: acquisition invalidation
  Counters c;
  c.fault = "sink: write: No space left on device";
  const Verdict v = assess(c);
  EXPECT_FALSE(v.complete);
  EXPECT_TRUE(v.losses.empty());
}

TEST(LossAlarm, RaisedByTheLossOfOneIntervalNotOfTheRun) {
  // Control: loss alarm
  LossAlarm a{0.01};
  EXPECT_FALSE(a.update(0, 100'000));
  EXPECT_FALSE(a.update(500, 1'000'000)) << "0.06% of the interval";
  EXPECT_TRUE(a.update(600, 1'000'100)) << "100 of 200 sent in this interval";
}

TEST(LossAlarm, StaysRaisedUntilAcknowledged) {
  // Control: loss alarm
  LossAlarm a{0.01};
  ASSERT_TRUE(a.update(50, 50));
  EXPECT_TRUE(a.update(50, 10'000)) << "the loss stopped, the alarm did not";
  a.acknowledge();
  EXPECT_FALSE(a.raised());
  EXPECT_FALSE(a.update(50, 20'000));
}

TEST(LossAlarm, ANewRunStartsAfresh) {
  // Control: loss alarm
  LossAlarm a{0.01};
  EXPECT_FALSE(a.update(10, 1'000'000));
  EXPECT_FALSE(a.update(0, 1'000)) << "counters went back to 0: a new run, not a huge loss";
  EXPECT_TRUE(a.update(100, 1'100));
}

TEST(LossAlarm, ZeroToleranceRaisesOnAnyLoss) {
  // Control: loss alarm
  LossAlarm a{0.0};
  EXPECT_FALSE(a.update(0, 1'000));
  EXPECT_TRUE(a.update(1, 1'000'000));
}

TEST(LossAlarm, RejectsAThresholdOutsideItsRange) {
  // Control: loss alarm
  EXPECT_THROW(LossAlarm{-0.1}, std::invalid_argument);
  EXPECT_THROW(LossAlarm{1.0}, std::invalid_argument);
}
