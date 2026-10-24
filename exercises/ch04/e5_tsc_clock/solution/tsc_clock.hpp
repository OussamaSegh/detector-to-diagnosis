// SPDX-License-Identifier: MIT
// Exercise 4.5: a TSC-based clock calibrated against CLOCK_MONOTONIC.
#pragma once

#include <chrono>
#include <cstdint>
#include <string_view>

namespace ex {

// Raw time-stamp counter on x86-64; 0 elsewhere.
[[nodiscard]] std::uint64_t read_tsc() noexcept;

// True if the "flags" line contains both constant_tsc and nonstop_tsc.
[[nodiscard]] bool tsc_is_invariant(std::string_view cpuinfo_text);

[[nodiscard]] std::int64_t monotonic_ns() noexcept;

class TscClock {
 public:
  [[nodiscard]] static TscClock calibrate(std::chrono::nanoseconds duration);

  // Estimate of CLOCK_MONOTONIC, in nanoseconds.
  [[nodiscard]] std::int64_t now_ns() const noexcept;
  [[nodiscard]] double ticks_per_us() const noexcept { return ns_per_tick_ > 0.0 ? 1000.0 / ns_per_tick_ : 0.0; }

 private:
  std::uint64_t base_tsc_ = 0;
  std::int64_t base_ns_ = 0;
  double ns_per_tick_ = 0.0;
};

}  // namespace ex
