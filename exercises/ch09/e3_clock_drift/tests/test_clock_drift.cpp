// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "clock_drift.hpp"

using namespace ex93;

namespace {

struct Residuals {
  double mean = 0;
  double stddev = 0;
  double max_abs = 0;
};

// Time differences of the corrected pairs: zero plus the jitter, if the
// correction works.
Residuals residuals(const Recording& r) {
  const ClockCorrection ca{r.sync_a, r.sync_period_ps};
  const ClockCorrection cb{r.sync_b, r.sync_period_ps};
  std::vector<double> d;
  for (const auto& [ta, tb] : r.pairs) {
    d.push_back(cb.to_global(tb) - ca.to_global(ta));
  }
  Residuals out;
  for (double x : d) {
    out.mean += x;
  }
  out.mean /= static_cast<double>(d.size());
  for (double x : d) {
    out.stddev += (x - out.mean) * (x - out.mean);
    out.max_abs = std::max(out.max_abs, std::abs(x));
  }
  out.stddev = std::sqrt(out.stddev / static_cast<double>(d.size() - 1));
  return out;
}

// Board A runs 10 ppm fast, board B 10 ppm slow: 20 ppm apart, 20 us per second.
const BoardClock board_a{3'000'000.0, +10.0};
const BoardClock board_b{-1'500'000.0, -10.0};

}  // namespace

TEST(ClockDrift, TheProblem) {
  const auto r = record(board_a, board_b, 1.0, 10'000, 0.001, 0.0, 0.0, 1);
  const auto& [a0, b0] = r.pairs.front();
  const auto& [a1, b1] = r.pairs.back();
  const double drift_ps = static_cast<double>((b1 - a1) - (b0 - a0));
  EXPECT_NEAR(drift_ps, -20e6, 0.5e6) << "20 us in a second: thousands of coincidence windows";
}

TEST(ClockDrift, IdealSyncRemovesOffsetAndDrift) {
  const auto r = record(board_a, board_b, 1.0, 10'000, 0.001, 0.0, 0.0, 2);
  const auto res = residuals(r);
  EXPECT_LT(std::abs(res.mean), 1.0);
  EXPECT_LT(res.max_abs, 5.0) << "only rounding to 1 ps remains";
}

TEST(ClockDrift, WithJitterTheResidualIsTheJitter) {
  // 100 ps per photon (141 ps on the difference), sync stamps with 20 ps.
  const auto r = record(board_a, board_b, 2.0, 20'000, 0.001, 100.0, 20.0, 3);
  const auto res = residuals(r);
  EXPECT_LT(std::abs(res.mean), 5.0);
  EXPECT_LT(res.stddev, 160.0) << "141 ps from the photons, a little from the sync stamps";
  EXPECT_GT(res.stddev, 130.0);
}

TEST(ClockDrift, ACoarseSyncStillWorksForConstantDrift) {
  // One sync per second is enough while the drift does not change.
  const auto r = record(board_a, board_b, 3.0, 5'000, 1.0, 100.0, 20.0, 4);
  const auto res = residuals(r);
  // With 4 sync stamps per board, the stamps' own 20 ps jitter sets the mean
  // error: about 0.53 * 20 ps per board, 15 ps for the difference, so 60 ps
  // is 4 sigma. Correcting only the offset leaves a mean error of microseconds.
  EXPECT_LT(std::abs(res.mean), 60.0);
  EXPECT_LT(res.stddev, 160.0);
}

TEST(ClockDrift, DriftFromTheDataAlone) {
  const auto r = record(board_a, board_b, 2.0, 20'000, 0.001, 100.0, 20.0, 5);
  // B relative to A: (1 - 10e-6) / (1 + 10e-6) - 1 = -19.9998 ppm.
  EXPECT_NEAR(estimate_relative_drift_ppm(r.pairs), -20.0, 0.05);
  const auto same = record(board_a, board_a, 2.0, 20'000, 0.001, 100.0, 20.0, 6);
  EXPECT_NEAR(estimate_relative_drift_ppm(same.pairs), 0.0, 0.05);
}
