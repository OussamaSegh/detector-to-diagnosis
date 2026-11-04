// SPDX-License-Identifier: MIT
#include "pulse/pulse.hpp"

#include <cassert>

namespace pulse {

Pulse integrate(std::span<const std::int16_t> samples, std::int16_t baseline) noexcept {
  Pulse p;
  for (std::size_t i = 0; i < samples.size(); ++i) {
    if (samples[i] > baseline) {
      p.area += samples[i] - baseline;
    }
    if (samples[i] > samples[p.peak]) {
      p.peak = i;
    }
  }
#if PULSE_CHECKED
  // How the library is built, not how it is used: its own checks.
  assert(samples.empty() || p.peak < samples.size());
#endif
  return p;
}

}  // namespace pulse
