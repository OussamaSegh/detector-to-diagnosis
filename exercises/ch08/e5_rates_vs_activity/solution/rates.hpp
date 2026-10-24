// SPDX-License-Identifier: MIT
// Exercise 8.5: coincidence rates versus activity, from the simulator's truth.
#pragma once

#include <span>
#include <vector>

#include "minidaq/sim/truth_counter.hpp"

namespace ex85 {

struct RatePoint {
  double activity_bq = 0.0;
  double decays_per_s = 0.0;
  double trues_per_s = 0.0;
  double scatters_per_s = 0.0;
  double randoms_per_s = 0.0;
};

// One simulation per activity: the brain phantom of minidaq_sim (a uniform
// cylinder of radius 80 mm and length 100 mm in a water cylinder of radius
// 90 mm and length 180 mm), counted with `window`.
[[nodiscard]] std::vector<RatePoint> sweep(std::span<const double> activities_bq, double seconds,
                                           const minidaq::sim::CountingWindow& window);

struct PowerLaw {
  double exponent = 0.0;   // k in y = a x^k
  double prefactor = 0.0;  // a
};

// Least-squares fit of y = a x^k. All values must be positive.
[[nodiscard]] PowerLaw fit_power_law(std::span<const double> x, std::span<const double> y);

}  // namespace ex85
