// SPDX-License-Identifier: MIT
// Exercise 19.4 solution: an oracle example and a metamorphic relation for run().
#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <random>
#include <vector>

#include "subject.hpp"

namespace {

using ex19::Pair;
using ex19::Single;

constexpr std::int64_t kWindow = 5;

TEST(Batching, PairsAHandWorkedStream) {
  const std::vector<Single> singles{{0, 1}, {3, 2}, {20, 3}, {24, 4}, {50, 5}};
  const std::vector<Pair> expected{{{0, 1}, {3, 2}}, {{20, 3}, {24, 4}}};
  EXPECT_EQ(ex19::run(singles, singles.size(), kWindow), expected);
}

// The oracle part: with two candidates in a window the first is the partner, and the third single
// opens its own window. Batching cannot show this; only a worked example can.
TEST(Batching, TheFirstCandidateIsThePartner) {
  const std::vector<Single> singles{{0, 1}, {2, 2}, {4, 3}, {30, 4}};
  const std::vector<Pair> expected{{{0, 1}, {2, 2}}};
  EXPECT_EQ(ex19::run(singles, singles.size(), kWindow), expected);
}

TEST(Batching, TiesAreTakenInCrystalOrder) {
  const std::vector<Single> singles{{0, 9}, {0, 4}, {1, 7}};
  const std::vector<Pair> expected{{{0, 4}, {0, 9}}};
  EXPECT_EQ(ex19::run(singles, singles.size(), kWindow), expected);
}

// A stream with the features that boundaries break: gaps shorter and longer than the window, and
// singles with the same time in descending crystal order (a tie can straddle a boundary only if
// the generator makes ties).
std::vector<Single> stream(std::uint32_t seed, std::size_t n) {
  std::mt19937 rnd{seed};
  std::uniform_int_distribution<std::int64_t> gap{0, 3 * kWindow};
  std::uniform_int_distribution<int> crystal{0, 15};
  std::bernoulli_distribution tie{0.3};
  std::vector<Single> out;
  std::int64_t t = 0;
  for (std::size_t i = 0; i < n; ++i) {
    t += tie(rnd) ? 0 : gap(rnd);
    out.push_back({t, static_cast<std::uint16_t>(crystal(rnd))});
  }
  return out;
}

// [snippet:metamorphic]
// The metamorphic relation: the same stream in batches of any size gives the same pairs as in one
// batch. Batch sizes 1 to 17 put boundaries everywhere, and sizes that do not divide the length
// leave a short last batch.
TEST(Batching, TheBatchSizeDoesNotChangeThePairs) {
  for (std::uint32_t seed = 1; seed <= 50; ++seed) {
    const auto singles = stream(seed, 101);
    const auto whole = ex19::run(singles, singles.size(), kWindow);
    ASSERT_FALSE(whole.empty());
    for (std::size_t b = 1; b <= 17; ++b) {
      ASSERT_EQ(ex19::run(singles, b, kWindow), whole) << "seed " << seed << ", batch size " << b;
    }
  }
}
// [/snippet:metamorphic]

// Invariants that hold whatever the batching: every pair is inside its window and in order, and
// no single is used twice.
TEST(Batching, EveryPairIsInItsWindowAndUsesTwoSingles) {
  for (std::uint32_t seed = 1; seed <= 50; ++seed) {
    const auto singles = stream(seed, 101);
    const auto pairs = ex19::run(singles, 7, kWindow);
    std::size_t used = 0;
    for (const Pair& p : pairs) {
      EXPECT_GE(p.partner.time, p.opener.time);
      EXPECT_LE(p.partner.time - p.opener.time, kWindow);
      used += 2;
    }
    EXPECT_LE(used, singles.size());
  }
}

}  // namespace
