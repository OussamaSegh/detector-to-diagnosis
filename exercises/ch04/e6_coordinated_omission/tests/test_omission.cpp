// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include "omission.hpp"

namespace {

constexpr std::int64_t us = 1000;
constexpr std::int64_t ms = 1000 * us;
constexpr std::size_t requests = 10'000;
constexpr std::size_t stalled = 5'000;

ex::ClosedLoopRun stalled_run() {
  return ex::simulate_closed_loop(requests, 1 * ms, [](std::size_t i) { return i == stalled ? 200 * ms : 100 * us; });
}

}  // namespace

TEST(Omission, SimulationWaitsForTheStall) {
  const auto run = stalled_run();
  ASSERT_EQ(run.end.size(), requests);
  EXPECT_EQ(run.start[0], 0);
  EXPECT_EQ(run.end[0], 100 * us);
  EXPECT_EQ(run.start[stalled + 1], run.end[stalled]);  // sent late, right after the stall
  EXPECT_EQ(run.start[stalled + 1], static_cast<std::int64_t>(stalled) * ms + 200 * ms);
  // Each fast request gains 0.9 ms on the schedule: 223 requests later the
  // tester is back on time.
  EXPECT_GT(run.start[stalled + 222], run.intended[stalled + 222]);
  EXPECT_EQ(run.start[stalled + 223], run.intended[stalled + 223]);
}

TEST(Omission, NaiveMeasurementHidesTheStall) {
  minidaq::LatencyHistogram h;
  ex::record_naive(h, stalled_run());
  EXPECT_EQ(h.count(), requests);
  EXPECT_LE(h.value_at_percentile(99.0), 101 * us);
  EXPECT_LE(h.value_at_percentile(99.99), 101 * us);
  EXPECT_GE(h.value_at_percentile(100.0), 200 * ms);  // only the maximum sees it
}

TEST(Omission, BothCorrectionsExposeTheStall) {
  minidaq::LatencyHistogram intended;
  ex::record_from_intended(intended, stalled_run());
  EXPECT_EQ(intended.count(), requests);
  EXPECT_GT(intended.value_at_percentile(99.0), 90 * ms);

  minidaq::LatencyHistogram corrected;
  const auto run = stalled_run();
  for (std::size_t i = 0; i < requests; ++i) {
    ex::record_corrected(corrected, run.end[i] - run.start[i], 1 * ms);
  }
  // 198 synthetic samples (199 ms down to 2 ms) for the requests not sent.
  EXPECT_EQ(corrected.count(), requests + 198);
  EXPECT_GT(corrected.value_at_percentile(99.0), 90 * ms);

  const auto a = static_cast<double>(intended.value_at_percentile(99.0));
  const auto b = static_cast<double>(corrected.value_at_percentile(99.0));
  EXPECT_NEAR(a / b, 1.0, 0.15);  // 110 ms and 99 ms: same story, different model
}

TEST(Omission, CorrectionLeavesFastSamplesAlone) {
  minidaq::LatencyHistogram h;
  ex::record_corrected(h, 100 * us, 1 * ms);
  ex::record_corrected(h, 1 * ms, 1 * ms);
  ex::record_corrected(h, 0, 0);  // no interval known: just record
  EXPECT_EQ(h.count(), 3U);
  ex::record_corrected(h, 3 * ms, 1 * ms);  // 3 ms, then 2 ms; 1 ms is not above the interval
  EXPECT_EQ(h.count(), 5U);
}
