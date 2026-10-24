// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <chrono>
#include <thread>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/paced_source.hpp"

using namespace std::chrono_literals;

TEST(PacedSource, NeverDeliversAheadOfTheClock) {
  // REQ: SRS-SIM-002
  // 200 k words/s: fast enough to pace in bursts, slow enough that a
  // ThreadSanitizer build on a shared CI runner can still keep up (it reached
  // only 0.78 M words/s against a 1 M target).
  constexpr double rate = 2e5;  // words per second
  minidaq::sim::PacedSource src{{}, rate, 512};
  std::vector<std::uint64_t> buf(4096);
  const std::int64_t t0 = minidaq::monotonic_ns();
  (void)src(buf);  // starts the clock
  while (minidaq::monotonic_ns() - t0 < 200'000'000) {
    const std::size_t n = src(buf);
    EXPECT_LE(n, 512U) << "max_burst";
    if (n == 0) {
      std::this_thread::sleep_for(100us);
    }
  }
  const double elapsed_s = static_cast<double>(minidaq::monotonic_ns() - t0) * 1e-9;
  const auto delivered = static_cast<double>(src.delivered());
  EXPECT_LE(delivered, rate * elapsed_s + 1.0);
  EXPECT_GE(delivered, 0.8 * rate * 0.2) << "should keep up with the rate";
}

TEST(PacedSource, WordsAreValidMdqP1) {
  minidaq::sim::PacedSource src{{}, 1e9, 4096};
  std::vector<std::uint64_t> buf(4096);
  std::this_thread::sleep_for(1ms);
  std::size_t n = 0;
  while (n == 0) {
    n = src(buf);
  }
  for (std::size_t i = 0; i < n; ++i) {
    EXPECT_LT(minidaq::packed::unpack(buf[i]).crystal, 18'432U);
  }
}

TEST(PacedSource, DueTimesFollowTheSchedule) {
  // REQ: SRS-SIM-003
  minidaq::sim::PacedSource src{{}, 1e6, 4096};  // one word per microsecond
  std::vector<std::uint64_t> buf(16);
  const std::int64_t before = minidaq::monotonic_ns();
  (void)src(buf);  // starts the clock
  const std::int64_t t0 = src.due_ns(0);
  EXPECT_GE(t0, before);
  EXPECT_LE(t0, minidaq::monotonic_ns());
  EXPECT_NEAR(static_cast<double>(src.due_ns(1000) - t0), 1e6, 1.0);  // 1000 words later: 1 ms
  EXPECT_NEAR(static_cast<double>(src.due_ns(1'000'000) - t0), 1e9, 1.0);
}

TEST(PacedSource, ReportsTheBacklogOfASlowReader) {
  // REQ: SRS-SIM-004
  minidaq::sim::PacedSource src{{}, 1e6, 16};  // one word per microsecond, at most 16 per call
  std::vector<std::uint64_t> buf(16);
  EXPECT_EQ(src.behind(minidaq::monotonic_ns()), 0U) << "not started";
  (void)src(buf);
  const std::int64_t t0 = src.due_ns(0);
  // 10 ms later without reading: about 10,000 words are due and not delivered.
  const auto b = src.behind(t0 + 10'000'000);
  EXPECT_GE(b, 9'900U);
  EXPECT_LE(b, 10'000U);
}
