// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <stdexcept>
#include <thread>

#include "stage_latencies.hpp"

namespace {
ex::StageLatencies two_stages() { return ex::StageLatencies{{"source", "sort"}}; }
}  // namespace

TEST(StageLatencies, IntervalSeesOnlyRecentSamples) {
  auto lat = two_stages();
  for (int i = 1; i <= 1000; ++i) {
    lat.record(1, std::int64_t{i} * 1000);  // 1 us .. 1 ms
  }
  const auto s1 = lat.snapshot();
  for (int i = 0; i < 1000; ++i) {
    lat.record(1, 5'000'000);  // then a slow second: 5 ms each
  }
  const auto s2 = lat.snapshot();

  const auto iv = lat.interval(s1, s2);
  ASSERT_EQ(iv.size(), 2U);
  EXPECT_EQ(iv[0].stage, "source");
  EXPECT_EQ(iv[0].count, 0U);
  EXPECT_EQ(iv[1].count, 1000U);
  EXPECT_NEAR(static_cast<double>(iv[1].p50_ns), 5e6, 5e6 * 0.008);
  EXPECT_GE(iv[1].p50_ns, 5'000'000);  // never under-reports
  EXPECT_EQ(iv[1].max_ns, iv[1].p999_ns);

  // The cumulative median still says "about 1 ms": the slow second is half of it.
  EXPECT_LT(lat.histogram(1).value_at_percentile(50.0), 1'100'000);

  const auto from_start = lat.interval(ex::StageLatencies{{"a", "b"}}.snapshot(), s2);
  EXPECT_EQ(from_start[1].count, 2000U);
}

TEST(StageLatencies, RejectsForeignOrReversedSnapshots) {
  auto lat = two_stages();
  const auto s1 = lat.snapshot();
  lat.record(0, 100);
  const auto s2 = lat.snapshot();
  EXPECT_THROW((void)lat.interval(s2, s1), std::invalid_argument);
  const auto other = ex::StageLatencies{{"only"}}.snapshot();
  EXPECT_THROW((void)lat.interval(other, s2), std::invalid_argument);
  auto truncated = s2;
  truncated[0].counts.pop_back();
  EXPECT_THROW((void)lat.interval(s1, truncated), std::invalid_argument);
}

TEST(StageLatencies, JsonFormatIsExact) {
  ex::StageLatencies lat{{"so\"urce", "decode"}};
  lat.record(0, 100);
  lat.record(0, 200);
  const auto iv = lat.interval(ex::StageLatencies{{"x", "y"}}.snapshot(), lat.snapshot());
  EXPECT_EQ(ex::to_json(iv, 1'000'000'000),
            "{\"interval_ms\":1000,\"stages\":["
            "{\"name\":\"so\\\"urce\",\"count\":2,\"p50_us\":0.100,\"p99_us\":0.200,\"p999_us\":0.200,"
            "\"max_us\":0.200},"
            "{\"name\":\"decode\",\"count\":0,\"p50_us\":0.000,\"p99_us\":0.000,\"p999_us\":0.000,"
            "\"max_us\":0.000}]}");
}

TEST(StageLatencies, SnapshotsWhileAWriterRecords) {
  ex::StageLatencies lat{{"source"}};
  std::atomic<bool> stop{false};
  std::atomic<std::uint64_t> written{0};
  auto prev = lat.snapshot();  // before the writer starts: the intervals must add up to everything
  std::thread writer{[&] {
    std::uint64_t n = 0;
    while (!stop.load(std::memory_order_relaxed)) {
      lat.record(0, static_cast<std::int64_t>(1000 + n % 5000));
      ++n;
    }
    written.store(n, std::memory_order_relaxed);
  }};

  std::uint64_t seen = 0;
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds{300};
  int intervals = 0;
  while (std::chrono::steady_clock::now() < deadline) {
    auto next = lat.snapshot();
    const auto iv = lat.interval(prev, next);  // must never throw: counts only grow
    seen += iv[0].count;
    if (iv[0].count > 0) {
      EXPECT_GE(iv[0].p50_ns, 1000);
      EXPECT_LE(iv[0].max_ns, 6100);
    }
    prev = std::move(next);
    ++intervals;
  }
  stop.store(true);
  writer.join();
  const auto last = lat.interval(prev, lat.snapshot());
  seen += last[0].count;
  EXPECT_EQ(seen, written.load());  // every sample in exactly one interval
  EXPECT_GT(intervals, 1);
}
