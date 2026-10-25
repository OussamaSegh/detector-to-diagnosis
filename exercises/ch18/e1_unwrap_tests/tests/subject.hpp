// SPDX-License-Identifier: MIT
// Exercise 18.1: the subject of your tests, a copy of MiniDAQ's TimeUnwrapper
// (minidaq/format/packed_single.hpp) with seven seeded mistakes. EX_MUTANT=0
// is the real code; 1 to 7 each change one thing a programmer could plausibly
// get wrong. Do not read the mutants before you have written your tests: write
// the tests from the specification (the comment on the class and SRS-FMT-012),
// then let the build tell you which mistakes they would let through.
#pragma once

#include <cstdint>

#include "minidaq/format/packed_single.hpp"

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

namespace ex {

using minidaq::Picoseconds;
using minidaq::packed::time_bits;
using minidaq::packed::time_lsb_ps;
using minidaq::packed::wrap_period_ps;

// Reconstructs absolute time from the wrapping 38-bit time code of MDQ-P1.
// Assumes consecutive words are less than half a wrap period (0.69 s) apart,
// in either direction: a word may arrive a little after a later one.
class TimeUnwrapper {
 public:
  constexpr TimeUnwrapper() noexcept = default;
  // Starting epoch, for streams that begin after one or more wraps.
#if EX_MUTANT == 5
  constexpr explicit TimeUnwrapper(std::int64_t /*epoch*/) noexcept {}
#else
  constexpr explicit TimeUnwrapper(std::int64_t epoch) noexcept : epoch_{epoch} {}
#endif

  [[nodiscard]] constexpr Picoseconds unwrap(std::uint64_t time_code) noexcept {
#if EX_MUTANT == 4
    constexpr std::uint64_t half = std::uint64_t{1} << time_bits;
#else
    constexpr std::uint64_t half = std::uint64_t{1} << (time_bits - 1);
#endif
    std::int64_t wraps = epoch_;
    if (has_last_) {
      if (time_code < last_ && last_ - time_code > half) {
#if EX_MUTANT == 6
        wraps = epoch_ + 1;
#else
        wraps = ++epoch_;
#endif
#if EX_MUTANT != 1
        last_ = time_code;
#endif
#if EX_MUTANT == 7
      } else if (time_code - last_ > half) {  // unsigned: wraps around when time_code < last_
#else
      } else if (time_code > last_ && time_code - last_ > half) {
#endif
#if EX_MUTANT == 2
        wraps = epoch_;
#else
        wraps = epoch_ - 1;
#endif
      } else if (time_code > last_) {
        last_ = time_code;
      }
    } else {
      last_ = time_code;
#if EX_MUTANT != 3
      has_last_ = true;
#endif
    }
    return Picoseconds{(wraps * wrap_period_ps) + static_cast<std::int64_t>(time_code) * time_lsb_ps};
  }
  [[nodiscard]] constexpr std::int64_t epoch() const noexcept { return epoch_; }

 private:
  std::int64_t epoch_{0};
  std::uint64_t last_{0};
  bool has_last_{false};
};

}  // namespace ex
