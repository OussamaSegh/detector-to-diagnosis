// SPDX-License-Identifier: MIT
// Exercise 11.1: count-rate curves and the NECR peak.
#pragma once

#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/sim/dead_time.hpp"

namespace ex111 {

struct Rates {  // per second, by ground truth
  double trues = 0.0;
  double scatters = 0.0;
  double randoms = 0.0;
};

// NECR = T^2 / (T + S + k R).
[[nodiscard]] double necr(const Rates& r, double k);
// S / (T + S); 0 when there are none.
[[nodiscard]] double scatter_fraction(const Rates& r);

// One point of the curve: the NEMA-style line source (minidaq_sim --nema 1)
// at `activity_bq` for `seconds`, with the front end `dead`, sorted with the
// default sorter but a 585 keV upper threshold, sectors at least 1 apart and a
// 120 mm field of view, and every prompt classified by its singles' truth.
struct Setup {
  double activity_bq = 0.0;
  double seconds = 0.0;
  minidaq::sim::DeadTimeConfig dead{};
  std::uint64_t seed = 11;
};
[[nodiscard]] Rates measure(const Setup& s);

struct CurvePoint {
  double activity_bq = 0.0;
  Rates rates;
};
// One point per activity, each simulated for decays / activity seconds (so
// every point has about the same number of decays).
[[nodiscard]] std::vector<CurvePoint> sweep(std::span<const double> activities_bq, double decays,
                                            const minidaq::sim::DeadTimeConfig& dead);

// The activity of the NECR(k) peak: the vertex of the parabola in ln(activity)
// through the highest point and its two neighbors. NaN if the highest point is
// the first or the last (the peak is not inside the sweep).
[[nodiscard]] double peak_activity(std::span<const CurvePoint> curve, double k);

}  // namespace ex111
