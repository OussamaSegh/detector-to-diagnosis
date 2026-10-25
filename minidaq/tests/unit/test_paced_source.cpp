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
  // 200 k words/s, paced in bursts. How much the source delivers in 0.2 s
  // depends on how often this thread runs, so the test checks the schedule,
  // not a throughput: a busy machine once delivered only 54% of the words due
  // (Chapter 16, CAPA-0001).
  constexpr double rate = 2e5;  // words per second
  minidaq::sim::PacedSource src{{}, rate, 512};
  std::vector<std::uint64_t> buf(4096);
  const std::int64_t t0 = minidaq::monotonic_ns();
  (void)src(buf);  // starts the clock
  while (minidaq::monotonic_ns() - t0 < 200'000'000) {
    const std::size_t n = src(buf);
    EXPECT_LE(n, 512U) << "max_burst";
    if (n == 0) {
      std::this_thread::sleep_for(100us);  // sleep: poll
    }
  }
  const double elapsed_s = static_cast<double>(minidaq::monotonic_ns() - t0) * 1e-9;
  const auto delivered = static_cast<double>(src.delivered());
  EXPECT_LE(delivered, rate * elapsed_s + 1.0);
  // It does deliver: once the next word is due (word number n is due when
  // n + 1 words are, plus 1 us for rounding), a call returns it.
  const std::uint64_t next = src.delivered();
  while (minidaq::monotonic_ns() < src.due_ns(next + 1) + 1'000) {
    std::this_thread::sleep_for(100us);  // sleep: poll
  }
  EXPECT_GT(src(buf), 0U) << "a due word is delivered";
}

TEST(PacedSource, WordsAreValidMdqP1) {
  minidaq::sim::PacedSource src{{}, 1e9, 4096};
  std::vector<std::uint64_t> buf(4096);
  std::this_thread::sleep_for(1ms);  // sleep: minimum (lets words become due)
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
