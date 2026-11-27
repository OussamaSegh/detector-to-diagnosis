// SPDX-License-Identifier: MIT
// Exercise 15.6 (A): tests of the agent's fault latch, one per cause the risk
// control names, and of what the operator reads.
#include <gtest/gtest.h>

#include <string>

#include "subject.hpp"

namespace {

using ex156::Cycle;
using ex156::FaultLatch;

TEST(Audit, ABoardThatDoesNotAnswerLatchesAfterThreeCycles) {
  FaultLatch latch{{}};
  latch.on_cycle({.reads_ok = false});
  latch.on_cycle({.reads_ok = false});
  EXPECT_FALSE(latch.latched());
  latch.on_cycle({.reads_ok = false});
  EXPECT_TRUE(latch.latched());
}

TEST(Audit, ABoardThatRefusesEveryWriteLatchesAfterThreeCycles) {
  // Reads answer, the setpoint is never written: the supply cannot reach it (RC-27).
  FaultLatch latch{{}};
  for (int i = 0; i < 3; ++i) {
    latch.on_cycle({.reads_ok = true, .writes_ok = false, .current_ua = 10});
  }
  EXPECT_TRUE(latch.latched());
}

TEST(Audit, FailuresOfReadsAndWritesInTurnAreOneRunOfFailedCycles) {
  FaultLatch latch{{}};
  latch.on_cycle({.reads_ok = false});
  latch.on_cycle({.reads_ok = true, .writes_ok = false});
  latch.on_cycle({.reads_ok = false});
  EXPECT_TRUE(latch.latched());
}

TEST(Audit, AGoodCycleEndsARunOfFailures) {
  FaultLatch latch{{}};
  for (int i = 0; i < 10; ++i) {
    latch.on_cycle({.writes_ok = false});
    latch.on_cycle({.writes_ok = false});
    latch.on_cycle({});
  }
  EXPECT_FALSE(latch.latched());
}

TEST(Audit, AMeasuredCurrentAboveTheLimitLatchesAndSaysSo) {
  FaultLatch latch{{}};
  latch.on_cycle({.current_ua = 501});
  ASSERT_TRUE(latch.latched());
  EXPECT_NE(latch.reason().find("501 uA is above the limit 500 uA"), std::string::npos)
      << latch.reason();
}

TEST(Audit, TheBoardsOwnTripLatchesAndDoesNotClaimAReadingAboveTheLimit) {
  // The board's comparator is faster than the loop: the reading may be below the limit.
  FaultLatch latch{{}};
  latch.on_cycle({.board_overcurrent = true, .current_ua = 120});
  ASSERT_TRUE(latch.latched());
  EXPECT_EQ(latch.reason().find("above the limit"), std::string::npos) << latch.reason();
  EXPECT_NE(latch.reason().find("board"), std::string::npos) << latch.reason();
}

TEST(Audit, AFaultStaysLatchedUntilAcknowledged) {
  FaultLatch latch{{}};
  latch.on_cycle({.current_ua = 900});
  latch.on_cycle({.current_ua = 10});
  EXPECT_TRUE(latch.latched());
  latch.acknowledge();
  EXPECT_FALSE(latch.latched());
  latch.on_cycle({.current_ua = 10});
  EXPECT_FALSE(latch.latched());
}

}  // namespace
