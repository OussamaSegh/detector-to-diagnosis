// SPDX-License-Identifier: MIT
// MiniDAQ - latency over an interval, from two snapshots of a histogram
// (Exercise 4.3, adopted by the control API in Chapter 6).
//
// A LatencyHistogram is cumulative and must not be reset while its stage
// writes to it. To answer "what was the p99.9 over the last second?", copy the
// bucket counts now and then, and subtract two copies. Snapshots allocate:
// take them on a monitoring thread, never on the hot path.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>

#include "minidaq/metrics/latency_histogram.hpp"

namespace minidaq {

struct HistogramCounts {
  std::vector<std::uint64_t> counts;  // one entry per bucket
};

[[nodiscard]] inline HistogramCounts snapshot_counts(const LatencyHistogram& h) {
  HistogramCounts s;
  s.counts.resize(h.bucket_count());
  for (std::size_t i = 0; i < h.bucket_count(); ++i) {
    s.counts[i] = h.count_at(i);
  }
  return s;
}

// [snippet:interval]
// Percentiles of the values recorded between `before` and `after`, at bucket
// resolution (min, max and percentiles are bucket bounds; mean and overflows
// are not tracked per interval and stay 0). The count is the sum of the bucket
// deltas, not the difference of count(): record() bumps the bucket before the
// total, so a snapshot's total can disagree with its buckets. Snapshots of a
// different histogram, or in the wrong order, give an empty summary.
[[nodiscard]] inline LatencySummary interval_summary(const LatencyHistogram& h, const HistogramCounts& before,
                                                     const HistogramCounts& after) {
  LatencySummary s;
  const auto& b = before.counts;
  const auto& a = after.counts;
  if (a.size() != h.bucket_count() || b.size() != a.size()) {
    return s;
  }
  std::uint64_t n = 0;
  std::size_t lo = a.size();
  std::size_t hi = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    if (a[i] < b[i]) {
      return LatencySummary{};
    }
    if (a[i] != b[i]) {
      n += a[i] - b[i];
      lo = std::min(lo, i);
      hi = i;
    }
  }
  s.count = n;
  if (n == 0) {
    return s;
  }
  const auto at = [&](double percent) {
    auto rank = static_cast<std::uint64_t>(std::ceil(percent / 100.0 * static_cast<double>(n) - 1e-9));
    rank = std::clamp<std::uint64_t>(rank, 1, n);
    std::uint64_t seen = 0;
    for (std::size_t i = lo; i <= hi; ++i) {
      seen += a[i] - b[i];
      if (seen >= rank) {
        return static_cast<std::int64_t>(h.highest_in(i));
      }
    }
    return static_cast<std::int64_t>(h.highest_in(hi));
  };
  s.min = static_cast<std::int64_t>(h.lowest_in(lo));
  s.max = static_cast<std::int64_t>(h.highest_in(hi));
  s.p50 = at(50.0);
  s.p90 = at(90.0);
  s.p99 = at(99.0);
  s.p999 = at(99.9);
  s.p9999 = at(99.99);
  return s;
}
// [/snippet:interval]

}  // namespace minidaq
