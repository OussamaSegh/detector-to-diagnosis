// SPDX-License-Identifier: MIT
// Exercise 32.1: a small library to install. The pulse of a digitized waveform: its area above
// a baseline and the index of its peak.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>

namespace pulse {

struct Pulse {
  std::int64_t area = 0;  // sum of (sample - baseline) over the samples above the baseline
  std::size_t peak = 0;   // index of the largest sample
};

// The pulse of `samples` above `baseline`. An empty span gives a pulse of area 0 at index 0.
[[nodiscard]] Pulse integrate(std::span<const std::int16_t> samples,
                              std::int16_t baseline) noexcept;

}  // namespace pulse
