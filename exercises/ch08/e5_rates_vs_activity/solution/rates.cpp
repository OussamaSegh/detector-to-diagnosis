// SPDX-License-Identifier: MIT
#include "rates.hpp"

#include <cmath>
#include <cstdint>

#include "minidaq/sim/detector_simulator.hpp"

namespace ex85 {

// [snippet:sweep]
std::vector<RatePoint> sweep(std::span<const double> activities_bq, double seconds,
                             const minidaq::sim::CountingWindow& window) {
  using namespace minidaq::sim;
  std::vector<RatePoint> points;
  std::uint64_t seed = 1;
  for (const double a : activities_bq) {
    SimulatorConfig cfg;
    cfg.activity_bq = a;
    cfg.source = {SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
    cfg.phantom = {90.0, 180.0};
    cfg.seed = seed++;  // independent runs
    DetectorSimulator sim{cfg};
    const auto singles = sim.generate_until(minidaq::Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
    const CoincidenceCounts c = count_coincidences(singles, window);
    points.push_back({a, static_cast<double>(sim.stats().decays) / seconds, static_cast<double>(c.trues) / seconds,
                      static_cast<double>(c.scatters) / seconds, static_cast<double>(c.randoms) / seconds});
  }
  return points;
}
// [/snippet:sweep]

// [snippet:fit]
// log y = log a + k log x: ordinary least squares on the logarithms.
PowerLaw fit_power_law(std::span<const double> x, std::span<const double> y) {
  double sx = 0.0;
  double sy = 0.0;
  double sxx = 0.0;
  double sxy = 0.0;
  const auto n = static_cast<double>(x.size());
  for (std::size_t i = 0; i < x.size(); ++i) {
    const double lx = std::log(x[i]);
    const double ly = std::log(y[i]);
    sx += lx;
    sy += ly;
    sxx += lx * lx;
    sxy += lx * ly;
  }
  const double k = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  return {k, std::exp((sy - k * sx) / n)};
}
// [/snippet:fit]

}  // namespace ex85
