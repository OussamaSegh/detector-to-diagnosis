// SPDX-License-Identifier: MIT
// MiniDAQ - monotonic time in nanoseconds (Chapter 4).
//
// std::chrono::steady_clock is CLOCK_MONOTONIC on Linux: it never jumps
// backwards (unlike CLOCK_REALTIME, which NTP and the operator can step), and
// glibc serves it from the vDSO without a system call. Host time like this is
// for measuring the software; event time comes from the detector (Chapter 9).
#pragma once

#include <chrono>
#include <cstdint>

namespace minidaq {

[[nodiscard]] inline std::int64_t monotonic_ns() noexcept {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

}  // namespace minidaq
