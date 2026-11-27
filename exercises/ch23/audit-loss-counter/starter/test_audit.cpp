// SPDX-License-Identifier: MIT
// Exercise 23.5 (A): your tests of the agent's loss counter (tests/subject.hpp).
// The acceptance builds them against the corrected change, where they must
// pass, and against the agent's change and each of its defects, where they
// must fail. Write them from change/SPEC.md and from what this chapter says a
// network does to datagrams.
#include <gtest/gtest.h>

#include "subject.hpp"

namespace {

TEST(Audit, OnePacketMissingIsOneLost) {
  ex235::LossCounter c;
  for (const std::uint32_t s : {1U, 2U, 4U}) {
    c.offer(s);
  }
  EXPECT_EQ(c.stats().lost, 1U);
}

// TODO: everything else a network does to datagrams (loss, reordering,
// duplication), the wrap of the numbering, and a link that restarts.

}  // namespace
