// SPDX-License-Identifier: MIT
// Exercise 7.6 (A): your tests of the agent's change to the settings reader
// (tests/subject.hpp). The acceptance builds them against the corrected
// change, where they must pass, and against the agent's change and each of its
// defects, where they must fail. Write them from change/SPEC.md and from what
// this chapter says about input you did not choose.
#include <gtest/gtest.h>

#include "subject.hpp"

namespace {

TEST(Audit, ReadsAWindowInNanoseconds) {
  const auto s = ex76::read_settings("schema_version = 2.2\ncoincidence_window_ns = 4.5\n");
  ASSERT_TRUE(s.has_value());
  EXPECT_DOUBLE_EQ(s->coincidence_window_ns, 4.5);
}

// TODO: what may a settings file hold that the agent's own tests never tried?
// Think of what a fuzzer would send, and of every way a version can be wrong.

}  // namespace
