// SPDX-License-Identifier: MIT
#include <pulse/pulse.hpp>

#include <array>
#include <cstdint>
#include <cstdio>

#ifdef PULSE_CHECKED
#error "PULSE_CHECKED is how pulse is built; a user of pulse must not inherit it"
#endif

int main() {
  constexpr std::array<std::int16_t, 5> samples{100, 120, 140, 110, 90};
  const auto p = pulse::integrate(samples, 100);
  std::printf("area %lld peak %zu\n", static_cast<long long>(p.area), p.peak);
  return 0;
}
