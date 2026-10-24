// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <vector>

#include "rates.hpp"

namespace {

const std::vector<ex85::RatePoint>& points() {
  static const std::vector<ex85::RatePoint> p = [] {
    constexpr std::array<double, 4> activities{1e6, 2e6, 4e6, 8e6};
    return ex85::sweep(activities, 0.2, {minidaq::Picoseconds{10'000}, 100.0, 1000.0});
  }();
  return p;
}

ex85::PowerLaw fit(double ex85::RatePoint::*field) {
  std::vector<double> x;
  std::vector<double> y;
  for (const auto& p : points()) {
    x.push_back(p.activity_bq);
    y.push_back(p.*field);
  }
  return ex85::fit_power_law(x, y);
}

}  // namespace

TEST(Rates, FitsExactPowerLaws) {
  const std::vector<double> x{1.0, 2.0, 5.0, 10.0};
  std::vector<double> y;
  for (double v : x) {
    y.push_back(3.0 * std::pow(v, 1.7));
  }
  const auto f = ex85::fit_power_law(x, y);
  EXPECT_NEAR(f.exponent, 1.7, 1e-9);
  EXPECT_NEAR(f.prefactor, 3.0, 1e-9);
}

// One test, because the sweep takes most of the time (CTest runs every test in
// its own process, so separate tests would each repeat it).
TEST(Rates, SweepMatchesThePhysics) {
  ASSERT_EQ(points().size(), 4U);
  for (const auto& p : points()) {
    EXPECT_NEAR(p.decays_per_s, p.activity_bq, 0.02 * p.activity_bq) << "rates are per second";
    EXPECT_GT(p.trues_per_s, 0.0);
    EXPECT_GT(p.randoms_per_s, 0.0);
  }
  EXPECT_NEAR(fit(&ex85::RatePoint::trues_per_s).exponent, 1.0, 0.05);
  EXPECT_NEAR(fit(&ex85::RatePoint::scatters_per_s).exponent, 1.0, 0.05);
  EXPECT_NEAR(fit(&ex85::RatePoint::randoms_per_s).exponent, 2.0, 0.1);

  // Sensitivity (trues per decay) falls slightly at the highest activity: a
  // window with three singles is a multiple, and the true pair in it is lost.
  const auto sensitivity = [](const ex85::RatePoint& p) { return p.trues_per_s / p.decays_per_s; };
  const double loss = 1.0 - sensitivity(points().back()) / sensitivity(points().front());
  EXPECT_GT(loss, 0.02);
  EXPECT_LT(loss, 0.10);
  double previous_fraction = 0.0;
  for (const auto& p : points()) {
    const double f = p.randoms_per_s / (p.trues_per_s + p.scatters_per_s + p.randoms_per_s);
    EXPECT_GT(f, previous_fraction) << "the randoms fraction rises with activity";
    previous_fraction = f;
  }
}
