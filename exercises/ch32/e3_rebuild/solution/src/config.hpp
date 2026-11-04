// SPDX-License-Identifier: MIT
// Exercise 32.3: the scanner's configuration. It gains a field every few weeks.
#pragma once

#include <string>

namespace rings {

struct Config {
  std::string site = "bench";
  double ring_radius_mm = 120.0;
  int crystals_per_ring = 96;
  double crystal_pitch_mm = 4.0;
  int rings = 8;
};

[[nodiscard]] Config default_config();

}  // namespace rings
