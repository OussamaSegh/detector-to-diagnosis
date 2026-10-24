// SPDX-License-Identifier: MIT
// Exercise 4.5 solution.
#include "tsc_clock.hpp"

#include <time.h>

#include <sstream>
#include <string>
#include <thread>

#if defined(__x86_64__)
#include <x86intrin.h>
#endif

namespace ex {

std::uint64_t read_tsc() noexcept {
#if defined(__x86_64__)
  return __rdtsc();
#else
  return 0;
#endif
}

bool tsc_is_invariant(std::string_view cpuinfo_text) {
  std::istringstream in{std::string{cpuinfo_text}};
  std::string line;
  while (std::getline(in, line)) {
    if (line.rfind("flags", 0) != 0) {
      continue;
    }
    const auto colon = line.find(':');
    if (colon == std::string::npos) {
      continue;
    }
    std::istringstream words{line.substr(colon + 1)};
    bool constant = false;
    bool nonstop = false;
    std::string w;
    while (words >> w) {
      constant = constant || w == "constant_tsc";
      nonstop = nonstop || w == "nonstop_tsc";
    }
    return constant && nonstop;  // the first CPU's flags are enough
  }
  return false;
}

std::int64_t monotonic_ns() noexcept {
  timespec ts{};
  ::clock_gettime(CLOCK_MONOTONIC, &ts);
  return std::int64_t{ts.tv_sec} * 1'000'000'000 + ts.tv_nsec;
}

// [snippet:calibrate]
TscClock TscClock::calibrate(std::chrono::nanoseconds duration) {
  // Bracket the clock read between two TSC reads and take the midpoint, so a
  // preemption between the two reads shows up as a wide bracket, not an error.
  const auto pair = [](std::uint64_t& tsc, std::int64_t& ns) {
    const std::uint64_t a = read_tsc();
    ns = monotonic_ns();
    const std::uint64_t b = read_tsc();
    tsc = a + (b - a) / 2;
  };
  TscClock c;
  pair(c.base_tsc_, c.base_ns_);
  std::this_thread::sleep_for(duration);
  std::uint64_t end_tsc = 0;
  std::int64_t end_ns = 0;
  pair(end_tsc, end_ns);
  if (end_tsc > c.base_tsc_) {
    c.ns_per_tick_ = static_cast<double>(end_ns - c.base_ns_) / static_cast<double>(end_tsc - c.base_tsc_);
  }
  return c;
}

std::int64_t TscClock::now_ns() const noexcept {
  const auto ticks = static_cast<double>(read_tsc() - base_tsc_);
  return base_ns_ + static_cast<std::int64_t>(ticks * ns_per_tick_);
}
// [/snippet:calibrate]

}  // namespace ex
