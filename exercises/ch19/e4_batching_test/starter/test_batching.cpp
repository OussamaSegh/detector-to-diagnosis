// SPDX-License-Identifier: MIT
// Exercise 19.4 starter: tests of run() in tests/subject.hpp. They pass, and so do all five
// seeded mistakes. Add tests until every mistake fails at least one of them (see the README).
#include <gtest/gtest.h>

#include <vector>

#include "subject.hpp"

namespace {

using ex19::Pair;
using ex19::Single;

TEST(Batching, PairsAHandWorkedStream) {
  const std::vector<Single> singles{{0, 1}, {3, 2}, {20, 3}, {24, 4}, {50, 5}};
  const std::vector<Pair> expected{{{0, 1}, {3, 2}}, {{20, 3}, {24, 4}}};
  EXPECT_EQ(ex19::run(singles, singles.size(), 5), expected);
}

// TODO: the result must not depend on the batch size. What does a stream need to contain for a
// mistake at a batch boundary to show?

}  // namespace
