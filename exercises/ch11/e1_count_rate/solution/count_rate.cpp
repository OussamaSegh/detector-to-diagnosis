// SPDX-License-Identifier: MIT
#include "count_rate.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <unordered_map>

#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"

namespace ex111 {

double necr(const Rates& r, double k) {
  const double d = r.trues + r.scatters + k * r.randoms;
  return d > 0.0 ? r.trues * r.trues / d : 0.0;
}

double scatter_fraction(const Rates& r) {
  return r.trues + r.scatters > 0.0 ? r.scatters / (r.trues + r.scatters) : 0.0;
}

// [snippet:measure]
Rates measure(const Setup& s) {
  using namespace minidaq;
  sim::SimulatorConfig cfg;
  cfg.activity_bq = s.activity_bq;
  cfg.seed = s.seed;
  cfg.phantom = {101.5, 700.0};
  cfg.source = {sim::SourceShape::Kind::cylinder, {0.0, -45.0, 0.0}, 1.6, 700.0};
  sim::DetectorSimulator simulator{cfg};
  const auto generated = simulator.generate_until(Picoseconds{static_cast<std::int64_t>(s.seconds * 1e12)});

  sim::DeadTime front_end{s.dead};  // the front end acts before anything is sorted
  std::vector<sim::TruthSingle> truth;
  truth.reserve(generated.size());
  front_end.push(generated, truth);
  front_end.flush(truth);

  std::vector<Single> singles;
  singles.reserve(truth.size());
  std::unordered_map<std::uint64_t, std::size_t> index;  // (time, crystal) -> truth
  index.reserve(truth.size());
  const auto key = [](const Single& x) {
    return (static_cast<std::uint64_t>(x.time.count()) << 15U) ^ x.crystal.value();
  };
  for (std::size_t i = 0; i < truth.size(); ++i) {
    singles.push_back(truth[i].single);
    index.emplace(key(truth[i].single), i);
  }

  SorterConfig sc;
  sc.energy_high_kev = 585.0;
  sc.min_sector_difference = 1;
  sc.fov_radius_mm = 120.0;
  CoincidenceSorter sorter{sc};
  std::vector<Coincidence> found;
  sorter.push(singles, found);
  sorter.flush(found);

  Rates r;
  for (const Coincidence& c : found) {
    if (c.kind != CoincidenceKind::prompt) {
      continue;  // delayed-window pairs estimate randoms; they are not prompts
    }
    const auto& a = truth[index.at(key(c.first))];
    const auto& b = truth[index.at(key(c.second))];
    if (a.decay != b.decay) {
      r.randoms += 1.0;
    } else if (a.scattered || b.scattered) {
      r.scatters += 1.0;  // one decay, but the line is wrong
    } else {
      r.trues += 1.0;
    }
  }
  r.trues /= s.seconds;
  r.scatters /= s.seconds;
  r.randoms /= s.seconds;
  return r;
}
// [/snippet:measure]

std::vector<CurvePoint> sweep(std::span<const double> activities_bq, double decays,
                              const minidaq::sim::DeadTimeConfig& dead) {
  std::vector<CurvePoint> curve;
  for (const double a : activities_bq) {
    curve.push_back({a, measure({.activity_bq = a, .seconds = decays / a, .dead = dead})});
  }
  return curve;
}

// [snippet:peak]
double peak_activity(std::span<const CurvePoint> curve, double k) {
  const auto best = std::max_element(curve.begin(), curve.end(), [k](const CurvePoint& a, const CurvePoint& b) {
    return necr(a.rates, k) < necr(b.rates, k);
  });
  if (best == curve.end() || best == curve.begin() || best + 1 == curve.end()) {
    return std::numeric_limits<double>::quiet_NaN();
  }
  // Vertex of the parabola through (x0, y0), (x1, y1), (x2, y2), x = ln A. The
  // grid is usually geometric (5, 10, 20, 50 ...), even in ln A, and the
  // curve's rise and fall are closer to symmetric there than in A.
  const double x0 = std::log(best[-1].activity_bq);
  const double x1 = std::log(best->activity_bq);
  const double x2 = std::log(best[1].activity_bq);
  const double y0 = necr(best[-1].rates, k);
  const double y1 = necr(best->rates, k);
  const double y2 = necr(best[1].rates, k);
  const double num = (x1 - x0) * (x1 - x0) * (y1 - y2) - (x1 - x2) * (x1 - x2) * (y1 - y0);
  const double den = (x1 - x0) * (y1 - y2) - (x1 - x2) * (y1 - y0);
  if (den == 0.0) {
    return best->activity_bq;  // three equal values: no better guess than the sample
  }
  return std::exp(x1 - 0.5 * num / den);
}
// [/snippet:peak]

}  // namespace ex111
