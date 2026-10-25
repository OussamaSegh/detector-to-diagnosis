// SPDX-License-Identifier: MIT
// Exercise 18.1: write at least fifteen tests of the time unwrapper in
// tests/subject.hpp, from its specification, until every seeded mistake fails
// at least one of them. Two tests are here to start from.
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "subject.hpp"

namespace {

constexpr std::int64_t lsb = minidaq::packed::time_lsb_ps;

std::uint64_t code_of(std::int64_t t_ps) {
  return static_cast<std::uint64_t>(t_ps / lsb) & minidaq::packed::time_mask;
}

TEST(Unwrap, TheFirstWordIsTakenAsItIs) {
  ex::TimeUnwrapper u;
  EXPECT_EQ(u.unwrap(12345).count(), 12345 * lsb);
}

TEST(Unwrap, AnIncreasingStreamIsUnchanged) {
  ex::TimeUnwrapper u;
  for (const std::int64_t t : {0, 5, 1'000, 2'000'000}) {
    EXPECT_EQ(u.unwrap(code_of(t)).count(), t);
  }
}

// TODO: the behaviors the specification promises and these two tests do not
// check: a wrap, the words after a wrap, many wraps, the largest code, a gap
// just under half a period, late words in the same period and from before a
// wrap, the epoch it reports, a starting epoch.

}  // namespace
