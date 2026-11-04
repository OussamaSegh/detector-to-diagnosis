// SPDX-License-Identifier: MIT
// Exercise 37.3: the subject of your review, a function an AI assistant wrote from requirement
// SRS-EX-037 (in README.md). It compiles without a warning, reads well and passes the two tests
// the assistant wrote with it. Your review is a set of tests written from the requirement.
//
// EX_MUTANT=0 is the function as the requirement wants it. 1 to 7 are versions an assistant could
// have written just as fluently: each passes the assistant's own tests, and each is wrong for
// some input the requirement covers. Your tests must pass on 0 and fail on every other.
#pragma once

#include <cstdint>

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

namespace assisted {

inline constexpr int mutant = EX_MUTANT;

inline constexpr std::uint64_t kPeriod = std::uint64_t{1} << 40;  // the counter wraps here
inline constexpr std::uint64_t kMask = kPeriod - 1;

// True when two singles with timestamps t_a and t_b (picoseconds of the 40-bit counter) are within
// window picoseconds of each other, the shorter way around the counter's circle.
inline bool coincident(std::uint64_t t_a, std::uint64_t t_b, std::uint64_t window) {
  if (mutant == 4) {
    t_a &= kMask;  // "normalize" the inputs instead of refusing them
    t_b &= kMask;
  } else if (t_a > kMask || t_b > kMask) {
    return false;
  }
  if (mutant != 7 && window >= kPeriod / 2) {
    return false;  // a window of half the period or more means nothing on a circle
  }
  std::uint64_t distance = 0;
  if (mutant == 2) {
    distance = t_a > t_b ? t_a - t_b : t_b - t_a;  // forgets the wrap
  } else if (mutant == 3) {
    distance = (t_b - t_a) & kMask;  // one way around only
  } else if (mutant == 5) {
    const std::uint32_t d = static_cast<std::uint32_t>(t_a > t_b ? t_a - t_b : t_b - t_a);
    distance = d < kPeriod - d ? d : kPeriod - d;  // 32 bits "are enough for a window"
  } else {
    const std::uint64_t d = (t_a - t_b) & kMask;
    const std::uint64_t other = (mutant == 6 ? kMask : kPeriod) - d;
    distance = d < other ? d : other;
  }
  return mutant == 1 ? distance < window : distance <= window;
}

}  // namespace assisted
