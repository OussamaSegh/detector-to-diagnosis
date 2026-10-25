// SPDX-License-Identifier: MIT
// Exercise 18.1, a solution: sixteen tests of the time unwrapper, written from
// its specification. Each names the behavior it checks; the arrange-act-assert
// steps are kept visible, and each test checks one behavior.
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "subject.hpp"

namespace {

using minidaq::packed::time_mask;

constexpr std::uint64_t period_codes = std::uint64_t{1} << minidaq::packed::time_bits;  // codes per wrap
constexpr std::uint64_t half_codes = period_codes / 2;
constexpr std::int64_t period_ps = minidaq::packed::wrap_period_ps;
constexpr std::int64_t lsb = minidaq::packed::time_lsb_ps;

// The code the readout sends for absolute time t (a multiple of 5 ps).
std::uint64_t code_of(std::int64_t t_ps) { return static_cast<std::uint64_t>(t_ps / lsb) & time_mask; }

// Unwraps the codes of `times` with a fresh unwrapper and returns the result.
std::vector<std::int64_t> round_trip(const std::vector<std::int64_t>& times, std::int64_t epoch = 0) {
  ex::TimeUnwrapper u{epoch};
  std::vector<std::int64_t> out;
  for (const auto t : times) {
    out.push_back(u.unwrap(code_of(t)).count());
  }
  return out;
}

// --- Before the first wrap

TEST(Unwrap, TheFirstWordIsTakenAsItIs) {
  ex::TimeUnwrapper u;
  EXPECT_EQ(u.unwrap(12345).count(), 12345 * lsb);
}

TEST(Unwrap, CodesAreFivePicosecondsEach) {
  ex::TimeUnwrapper u;
  EXPECT_EQ(u.unwrap(1).count(), 5);
  EXPECT_EQ(u.unwrap(2).count(), 10);
}

TEST(Unwrap, AnIncreasingStreamIsUnchanged) {
  const std::vector<std::int64_t> t{0, 5, 1'000, 2'000'000, 500'000'000'000};
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, TheLargestCodeIsTheEndOfTheFirstPeriod) {
  ex::TimeUnwrapper u;
  EXPECT_EQ(u.unwrap(time_mask).count(), period_ps - lsb);
}

// --- Across a wrap

// [snippet:wrap]
TEST(Unwrap, OneWrapAddsOnePeriod) {
  const std::vector<std::int64_t> t{period_ps - 100, period_ps + 100};
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, TheWordsAfterAWrapStayInTheNewPeriod) {
  // The second and third words after the wrap must not be taken as another wrap.
  const std::vector<std::int64_t> t{period_ps - 100, period_ps + 100, period_ps + 200, period_ps + 300};
  EXPECT_EQ(round_trip(t), t);
}

// Times k/8 of a period apart for odd k: every step is a quarter period, well
// inside the precondition (less than half a period between words).
std::vector<std::int64_t> eighths(std::int64_t periods) {
  std::vector<std::int64_t> t;
  for (std::int64_t k = 1; k < 8 * periods; k += 2) {
    t.push_back(k * period_ps / 8 / lsb * lsb);
  }
  return t;
}

TEST(Unwrap, ManyWrapsInARow) {
  const auto t = eighths(10);
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, TheEpochCountsTheWraps) {
  ex::TimeUnwrapper u;
  for (const auto t : eighths(3)) {
    (void)u.unwrap(code_of(t));
  }
  EXPECT_EQ(u.epoch(), 2);
}

TEST(Unwrap, AGapJustUnderHalfAPeriodIsStillUnwrapped) {
  const std::int64_t gap = (static_cast<std::int64_t>(half_codes) - 1) * lsb;
  const std::vector<std::int64_t> t{period_ps - 1'000, period_ps - 1'000 + gap};
  EXPECT_EQ(round_trip(t), t);
}

// [/snippet:wrap]

// --- Late words (jitter between channels)

TEST(Unwrap, ALateWordInTheSamePeriod) {
  const std::vector<std::int64_t> t{1'000'000, 999'000, 1'001'000};
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, ALateWordFromBeforeTheWrap) {
  // The 100 ps word was sent before the wrap but arrives after a word from after it.
  const std::vector<std::int64_t> t{period_ps - 200, period_ps + 100, period_ps - 100};
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, ALateWordDoesNotMoveTheEpochBack) {
  const std::vector<std::int64_t> t{period_ps - 200, period_ps + 100, period_ps - 100, period_ps + 300};
  EXPECT_EQ(round_trip(t), t);
}

TEST(Unwrap, ALateWordDoesNotCountAsAWrap) {
  ex::TimeUnwrapper u;
  (void)u.unwrap(code_of(1'000'000));
  (void)u.unwrap(code_of(999'000));
  EXPECT_EQ(u.epoch(), 0);
}

// --- A starting epoch

TEST(Unwrap, AStartingEpochIsAddedToEveryTime) {
  const std::vector<std::int64_t> t{(5 * period_ps) + 1'000, (5 * period_ps) + 2'000};
  EXPECT_EQ(round_trip(t, 5), t);
}

TEST(Unwrap, AStartingEpochWrapsForward) {
  const std::vector<std::int64_t> t{(3 * period_ps) - 100, (3 * period_ps) + 100};
  EXPECT_EQ(round_trip(t, 2), t);
}

TEST(Unwrap, TheEpochIsReported) {
  const ex::TimeUnwrapper u{7};
  EXPECT_EQ(u.epoch(), 7);
}

}  // namespace
