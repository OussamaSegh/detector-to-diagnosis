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

// [snippet:correct]
// Piecewise linear: between sync k and k + 1 the board's clock is taken to run
// at a constant rate, measured by those two stamps. This removes the offset,
// the drift, and any slow change of the drift (temperature), to within the
// sync stamps' own jitter. Before the first and after the last stamp, the
// nearest interval is extrapolated.
double ClockCorrection::to_global(std::int64_t local_ps) const {
  auto it = std::upper_bound(sync_.begin(), sync_.end(), local_ps);
  std::size_t k = it == sync_.begin() ? 0 : static_cast<std::size_t>(it - sync_.begin()) - 1;
  k = std::min(k, sync_.size() - 2);
  const double l0 = static_cast<double>(sync_[k]);
  const double l1 = static_cast<double>(sync_[k + 1]);
  const double f = (static_cast<double>(local_ps) - l0) / (l1 - l0);
  return (static_cast<double>(k) + f) * period_ps_;
}
// [/snippet:correct]

// [snippet:estimate]
// Least-squares slope of d = tB - tA against tA. With true coincidences the
// photons' real time difference averages to zero, so the slope is the
// relative rate of the two clocks. In a real scanner, pairs are mixed with
// randoms; a robust fit (or the peak of a d histogram per time slice) is the
// version to use there.
double estimate_relative_drift_ppm(std::span<const std::pair<std::int64_t, std::int64_t>> pairs) {
  if (pairs.size() < 2) {
    return 0.0;
  }
  const double x0 = static_cast<double>(pairs.front().first);  // centre for numerical stability
  double sx = 0;
  double sy = 0;
  double sxx = 0;
  double sxy = 0;
  for (const auto& [ta, tb] : pairs) {
    const double x = static_cast<double>(ta) - x0;
    const double y = static_cast<double>(tb - ta);
    sx += x;
    sy += y;
    sxx += x * x;
    sxy += x * y;
  }
  const double n = static_cast<double>(pairs.size());
  const double slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  return slope * 1e6;
}
// [/snippet:estimate]

}  // namespace ex93
