// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <random>
#include <vector>

#include "minidaq/metrics/histogram_interval.hpp"
#include "minidaq/metrics/latency_histogram.hpp"

using minidaq::LatencyHistogram;

TEST(LatencyHistogram, EmptyIsAllZero) {
  LatencyHistogram h;
  const auto s = h.summary();
  EXPECT_EQ(s.count, 0U);
  EXPECT_EQ(h.value_at_percentile(99.0), 0);
}

TEST(LatencyHistogram, BucketBoundariesAreContiguous) {
  LatencyHistogram h{std::int64_t{1} << 30, 5};
  for (std::size_t i = 1; i < h.bucket_count(); ++i) {
    ASSERT_EQ(h.lowest_in(i), h.highest_in(i - 1) + 1) << "gap or overlap at bucket " << i;
    ASSERT_EQ(h.index_of(h.lowest_in(i)), i);
    ASSERT_EQ(h.index_of(h.highest_in(i)), i);
  }
}

TEST(LatencyHistogram, RelativeErrorBound) {
  // REQ: SRS-PERF-010
  constexpr unsigned bits = 7;
  LatencyHistogram h{std::int64_t{1} << 40, bits};
  std::mt19937_64 rng{7};
  for (int i = 0; i < 100'000; ++i) {
    const std::uint64_t v = rng() >> (24 + rng() % 40);  // spread over many magnitudes
    const std::size_t b = h.index_of(v);
    const double width = static_cast<double>(h.highest_in(b) - h.lowest_in(b) + 1);
    ASSERT_LE(width, std::max(1.0, static_cast<double>(v) / std::ldexp(1.0, bits))) << v;
  }
}

TEST(LatencyHistogram, PercentilesMatchExactWithinPrecision) {
  // REQ: SRS-PERF-010
  LatencyHistogram h;
  std::mt19937_64 rng{42};
  std::lognormal_distribution<double> d{10.0, 1.5};  // long-tailed, like real latencies
  std::vector<std::int64_t> v(200'000);
  for (auto& x : v) {
    x = static_cast<std::int64_t>(d(rng));
    h.record(x);
  }
  std::sort(v.begin(), v.end());
  for (double p : {50.0, 90.0, 99.0, 99.9, 99.99}) {
    const auto rank = static_cast<std::size_t>(std::ceil(p / 100.0 * static_cast<double>(v.size()) - 1e-9));
    const double exact = static_cast<double>(v[rank - 1]);
    const double got = static_cast<double>(h.value_at_percentile(p));
    EXPECT_GE(got, exact) << "p" << p << " must not under-report";
    EXPECT_LE(got, exact * (1.0 + 1.0 / 128.0) + 1.0) << "p" << p;
  }
  EXPECT_EQ(h.value_at_percentile(100.0), v.back());
  EXPECT_EQ(h.summary().min, v.front());
}

TEST(LatencyHistogram, SmallExactValues) {
  LatencyHistogram h;
  for (int i = 1; i <= 100; ++i) {
    h.record(i);
  }
  EXPECT_EQ(h.value_at_percentile(50.0), 50);
  EXPECT_EQ(h.value_at_percentile(99.0), 99);
  EXPECT_EQ(h.value_at_percentile(100.0), 100);
  EXPECT_DOUBLE_EQ(h.summary().mean, 50.5);
}

TEST(LatencyHistogram, OverflowIsClampedAndCounted) {
  LatencyHistogram h{1'000'000};
  h.record(10);
  h.record(5'000'000);
  h.record(-3);  // negative values count as 0
  const auto s = h.summary();
  EXPECT_EQ(s.count, 3U);
  EXPECT_EQ(s.overflows, 1U);
  EXPECT_EQ(s.max, 1'000'000);
  EXPECT_EQ(s.min, 0);
}

TEST(LatencyHistogram, MergeAndReset) {
  LatencyHistogram a;
  LatencyHistogram b;
  for (int i = 0; i < 1000; ++i) {
    a.record(100);
    b.record(10'000);
  }
  ASSERT_TRUE(a.merge(b));
  EXPECT_EQ(a.count(), 2000U);
  EXPECT_EQ(a.value_at_percentile(50.0), 100);
  EXPECT_GE(a.value_at_percentile(99.0), 10'000);
  LatencyHistogram other_shape{1000, 3};
  EXPECT_FALSE(a.merge(other_shape));
  a.reset();
  EXPECT_EQ(a.count(), 0U);
  EXPECT_EQ(a.summary().max, 0);
}

TEST(LatencyHistogram, FixedSmallFootprint) {
  LatencyHistogram h;  // defaults: up to 2^40 ns (about 18 minutes), 0.8% precision
  EXPECT_LT(h.memory_bytes(), 64U * 1024U);
}

TEST(LatencyHistogram, CountAtExposesBuckets) {
  minidaq::LatencyHistogram h;
  h.record(5);
  h.record(5);
  h.record(1'000'000);
  EXPECT_EQ(h.count_at(h.index_of(5)), 2U);
  EXPECT_EQ(h.count_at(h.index_of(1'000'000)), 1U);
  EXPECT_EQ(h.count_at(h.bucket_count()), 0U);  // out of range reads as empty
}

TEST(HistogramInterval, PercentilesOfOnlyTheValuesBetweenTwoSnapshots) {
  minidaq::LatencyHistogram h;
  for (int i = 0; i < 1000; ++i) {
    h.record(100);
  }
  const auto before = minidaq::snapshot_counts(h);
  for (int i = 0; i < 99; ++i) {
    h.record(5'000);
  }
  h.record(1'000'000);
  const auto after = minidaq::snapshot_counts(h);

  const auto s = minidaq::interval_summary(h, before, after);
  EXPECT_EQ(s.count, 100U);
  EXPECT_NEAR(static_cast<double>(s.p50), 5'000.0, 5'000.0 / 128);
  EXPECT_NEAR(static_cast<double>(s.p99), 5'000.0, 5'000.0 / 128);
  EXPECT_NEAR(static_cast<double>(s.max), 1e6, 1e6 / 128);
  EXPECT_LE(s.min, 5'000);
  EXPECT_GT(s.min, 4'900);
  EXPECT_EQ(h.summary().p50, 100) << "the cumulative view is unchanged";

  EXPECT_EQ(minidaq::interval_summary(h, after, after).count, 0U) << "nothing happened";
  EXPECT_EQ(minidaq::interval_summary(h, after, before).count, 0U) << "wrong order";
  minidaq::LatencyHistogram other{1000};
  EXPECT_EQ(minidaq::interval_summary(other, before, after).count, 0U) << "different histogram";
}
