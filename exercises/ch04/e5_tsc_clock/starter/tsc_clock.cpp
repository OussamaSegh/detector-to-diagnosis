// SPDX-License-Identifier: MIT
// Exercise 4.5 starter.
#include "tsc_clock.hpp"

#include <time.h>

namespace ex {

std::uint64_t read_tsc() noexcept {
  // TODO: __rdtsc() on x86-64.
  return 0;
}

bool tsc_is_invariant(std::string_view cpuinfo_text) {
  // TODO: find the "flags" line and look for whole words.
  (void)cpuinfo_text;
  return false;
}

std::int64_t monotonic_ns() noexcept {
  timespec ts{};
  ::clock_gettime(CLOCK_MONOTONIC, &ts);
  return std::int64_t{ts.tv_sec} * 1'000'000'000 + ts.tv_nsec;
}

TscClock TscClock::calibrate(std::chrono::nanoseconds duration) {
  // TODO: read both clocks, sleep, read both again.
  (void)duration;
  return {};
}

std::int64_t TscClock::now_ns() const noexcept {
  // TODO
  return 0;
}

}  // namespace ex
