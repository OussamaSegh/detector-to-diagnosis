// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "count_rate.hpp"

using ex111::CurvePoint;
using ex111::Rates;
using minidaq::Picoseconds;
using minidaq::sim::DeadTimeConfig;
using minidaq::sim::DeadTimeModel;

namespace {

// Half a million decays per point keeps the whole test near half a minute in a
// Debug build; the tolerances below are about four standard deviations or more.
constexpr double decays = 5e5;

const DeadTimeConfig front_end{DeadTimeModel::non_paralyzable, minidaq::sim::DeadTimeUnit::block,
                               Picoseconds{1'000'000}, true};

ex111::Setup at(double mbq, const DeadTimeConfig& dead = {}) {
  return {.activity_bq = mbq * 1e6, .seconds = decays / (mbq * 1e6), .dead = dead};
}

}  // namespace

TEST(CountRate, NecrByHand) {
  const Rates r{.trues = 100.0, .scatters = 50.0, .randoms = 25.0};
  EXPECT_DOUBLE_EQ(ex111::necr(r, 1.0), 10000.0 / 175.0);
  EXPECT_DOUBLE_EQ(ex111::necr(r, 2.0), 50.0);
  EXPECT_DOUBLE_EQ(ex111::necr(Rates{}, 1.0), 0.0);
  EXPECT_DOUBLE_EQ(ex111::scatter_fraction(r), 50.0 / 150.0);
}

TEST(CountRate, PeakIsInterpolated) {
  // NECR(A) = A exp(-A / 100), peak at exactly 100; the nearest sample is 120.
  std::vector<CurvePoint> curve;
  for (const double a : {30.0, 60.0, 120.0, 240.0}) {
    // T^2 / T = T: a curve with only trues has NECR = T.
    curve.push_back({a, Rates{.trues = a * std::exp(-a / 100.0)}});
  }
  EXPECT_NEAR(ex111::peak_activity(curve, 1.0), 100.0, 6.0);
  // Symmetric in ln A around 100: exactly 100.
  const std::vector<CurvePoint> sym{{50.0, Rates{.trues = 1.0}}, {100.0, Rates{.trues = 2.0}},
                                    {200.0, Rates{.trues = 1.0}}};
  EXPECT_NEAR(ex111::peak_activity(sym, 1.0), 100.0, 1e-9);
  // A curve that still rises at its end has no peak inside it.
  const std::vector<CurvePoint> rising{{10.0, Rates{.trues = 1.0}}, {20.0, Rates{.trues = 2.0}}};
  EXPECT_TRUE(std::isnan(ex111::peak_activity(rising, 1.0)));
}

TEST(CountRate, ScattersAreSeparated) {
  // The NEMA-style phantom scatters about a third of the coincidences.
  const Rates r = ex111::measure(at(20.0));
  EXPECT_GT(r.trues, 0.0);
  EXPECT_GT(ex111::scatter_fraction(r), 0.30);
  EXPECT_LT(ex111::scatter_fraction(r), 0.40);
}

TEST(CountRate, TruesGrowLinearlyAndRandomsQuadratically) {
  // Without dead time.
  const Rates lo = ex111::measure(at(50.0));
  const Rates hi = ex111::measure(at(100.0));
  const double trues = hi.trues / lo.trues;
  const double randoms = hi.randoms / lo.randoms;
  EXPECT_GT(trues, 1.7) << "trues ratio " << trues;
  EXPECT_LT(trues, 2.3) << "trues ratio " << trues;
  EXPECT_GT(randoms, 3.0) << "randoms ratio " << randoms;
  EXPECT_LT(randoms, 5.2) << "randoms ratio " << randoms;
}

TEST(CountRate, DeadTimeLowersTheRates) {
  const Rates ideal = ex111::measure(at(100.0));
  const Rates dead = ex111::measure(at(100.0, front_end));
  // A 1 us block dead time loses about a fifth of the singles at 100 MBq; a
  // coincidence needs both of its singles, and pile-up pushes some of the
  // recorded ones out of the energy window (the solution keeps about 45%).
  EXPECT_LT(dead.trues, 0.7 * ideal.trues);
}

TEST(CountRate, DeadTimeBringsThePeakDown) {
  const std::vector<double> activities{20e6, 50e6, 100e6, 200e6, 400e6};
  const auto curve = ex111::sweep(activities, decays, front_end);
  ASSERT_EQ(curve.size(), activities.size());
  const double peak = ex111::peak_activity(curve, 1.0);
  EXPECT_GT(peak, 40e6);
  EXPECT_LT(peak, 200e6);
}
