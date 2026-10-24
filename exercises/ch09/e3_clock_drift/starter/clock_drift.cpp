// SPDX-License-Identifier: MIT
#include "clock_drift.hpp"

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>

namespace ex93 {

Recording record(BoardClock a, BoardClock b, double seconds, double pair_rate_hz, double sync_period_s,
                 double jitter_ps, double sync_jitter_ps, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::exponential_distribution<double> gap{pair_rate_hz * 1e-12};
  // normal_distribution requires a standard deviation above zero; zero jitter
  // means an ideal clock, so draw nothing.
  auto normal = [&rng](double sigma) { return sigma > 0.0 ? std::normal_distribution<double>{0.0, sigma}(rng) : 0.0; };
  Recording r;
  r.sync_period_ps = sync_period_s * 1e12;
  const double end = seconds * 1e12;
  for (double t = gap(rng); t < end; t += gap(rng)) {
    r.pairs.emplace_back(std::llround(a.local_of(t) + normal(jitter_ps)), std::llround(b.local_of(t) + normal(jitter_ps)));
  }
  for (double t = 0.0; t <= end + r.sync_period_ps; t += r.sync_period_ps) {
    r.sync_a.push_back(std::llround(a.local_of(t) + normal(sync_jitter_ps)));
    r.sync_b.push_back(std::llround(b.local_of(t) + normal(sync_jitter_ps)));
  }
  return r;
}

ClockCorrection::ClockCorrection(std::span<const std::int64_t> sync_local, double sync_period_ps)
    : sync_(sync_local.begin(), sync_local.end()), period_ps_{sync_period_ps} {
  if (sync_.size() < 2 || !std::is_sorted(sync_.begin(), sync_.end())) {
    throw std::invalid_argument("ClockCorrection: need at least two sync stamps, in order");
  }
}

// TODO(9.3): this removes the board's offset, measured at the first sync
// pulse, and nothing else. Make the correction follow the drift.
double ClockCorrection::to_global(std::int64_t local_ps) const {
  return static_cast<double>(local_ps - sync_.front());
}

// TODO(9.3): estimate the relative drift of the two boards from the pairs
// alone. Hint: plot tB - tA against tA.
double estimate_relative_drift_ppm(std::span<const std::pair<std::int64_t, std::int64_t>> pairs) {
  (void)pairs;
  return 0.0;
}

}  // namespace ex93
