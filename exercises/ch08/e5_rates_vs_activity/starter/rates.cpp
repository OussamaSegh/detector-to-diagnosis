// SPDX-License-Identifier: MIT
#include "rates.hpp"

namespace ex85 {

std::vector<RatePoint> sweep(std::span<const double> activities_bq, double seconds,
                             const minidaq::sim::CountingWindow& window) {
  (void)activities_bq;
  (void)seconds;
  (void)window;
  return {};  // TODO: one simulation per activity
}

PowerLaw fit_power_law(std::span<const double> x, std::span<const double> y) {
  // TODO: this is a straight line through the raw values.
  double sx = 0, sy = 0, sxx = 0, sxy = 0;
  const auto n = static_cast<double>(x.size());
  for (std::size_t i = 0; i < x.size(); ++i) {
    sx += x[i];
    sy += y[i];
    sxx += x[i] * x[i];
    sxy += x[i] * y[i];
  }
  const double slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
  return {slope, (sy - slope * sx) / n};
}

}  // namespace ex85
