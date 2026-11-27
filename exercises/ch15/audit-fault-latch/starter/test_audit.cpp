// SPDX-License-Identifier: MIT
// Exercise 15.6 (A): your tests of the agent's fault latch (tests/subject.hpp).
// The acceptance builds them against the corrected change, where they must
// pass, and against the agent's change and each of its defects, where they
// must fail. Write them from change/SPEC.md and from the hazard the control
// cites: what must be true for the control to reduce that risk?
#include <gtest/gtest.h>

#include "subject.hpp"

namespace {

TEST(Audit, ABoardThatDoesNotAnswerLatchesAfterThreeCycles) {
  ex156::FaultLatch latch{{}};
  for (int i = 0; i < 3; ++i) {
    latch.on_cycle({.reads_ok = false});
  }
  EXPECT_TRUE(latch.latched());
}

// TODO: every cause of H-10 the control names, one test each, and what the
// operator reads in the reason.

}  // namespace
