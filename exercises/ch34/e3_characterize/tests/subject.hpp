// SPDX-License-Identifier: MIT
// Exercise 34.3: the subject of your characterization tests, a function from an older acquisition
// program: the live-time corrected count rate of a detector block, as its display showed it. No
// specification survives, and the people who wrote it have left. The code below is the only
// statement of what it does, and the display, the service tools and two analysis scripts depend
// on what it does today, quirks included.
//
// EX_MUTANT=0 is the function as it is. 1 to 7 are changes someone might make: some are mistakes,
// some are well-meant fixes of a quirk. A characterization test must catch both, because a
// change of behavior that nobody decided is a defect for everything that relies on the old one.
#pragma once

#include <cstdint>

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

namespace legacy {

inline constexpr int mutant = EX_MUTANT;

// counts: events in the interval; live_us: the time the block could count, in microseconds;
// real_us: the length of the interval, in microseconds. Returns events per second.
inline std::int64_t corrected_rate(std::int64_t counts, std::int64_t live_us,
                                   std::int64_t real_us) {
  if (real_us <= 0) {
    return mutant == 1 ? 0 : -1;  // no interval: an error code the display shows as "---"
  }
  if (counts < 0) {
    return mutant == 6 ? 0 : -2;  // a corrupt counter: another error code
  }
  if (live_us <= 0) {
    // A block that was dead the whole interval shows 0, not an error (mutant 2 "fixes" that).
    return mutant == 2 ? -1 : 0;
  }
  if (mutant != 3 && live_us > real_us) {
    live_us = real_us;  // a live time longer than the interval is a counter glitch
  }
  std::int64_t rate = counts * 1'000'000 / live_us;  // truncated
  if (mutant == 4) {
    rate = (counts * 1'000'000 + live_us / 2) / live_us;  // "fixed": rounded
  } else if (mutant == 7) {
    rate = counts / live_us * 1'000'000;
  }
  const std::int64_t display_limit = mutant == 5 ? 5'000'000 : 50'000'000;
  if (rate > display_limit) {
    rate = display_limit;
  }
  return rate;
}

}  // namespace legacy
