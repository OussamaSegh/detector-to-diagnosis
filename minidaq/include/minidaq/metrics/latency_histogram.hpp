// SPDX-License-Identifier: MIT
// MiniDAQ - fixed-memory latency histogram (Chapter 4).
//
// A log-linear histogram in the style of Gil Tene's HdrHistogram (this is not
// that library; see the chapter for the differences). Values below 2^(S+1)
// get one bucket each; above that, every power-of-two range is split into 2^S
// equal buckets, so the relative error of any reported value is below 2^-S
// (S = 7: under 0.8%). Memory is fixed at construction and record() never
// allocates, locks or makes a system call, so it is safe on the hot path.
//
// Threading: one writer thread calls record(); any thread may read (counts are
// relaxed atomics, so a reader sees a slightly stale but never torn view).
// reset() and merge() must not run concurrently with record().
#pragma once

#include <algorithm>
#include <atomic>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>

namespace minidaq {

struct LatencySummary {
  std::uint64_t count = 0;
  std::uint64_t overflows = 0;  // values above the configured maximum (counted in the top bucket)
  std::int64_t min = 0;
  std::int64_t max = 0;
  double mean = 0.0;
  std::int64_t p50 = 0;
  std::int64_t p90 = 0;
  std::int64_t p99 = 0;
  std::int64_t p999 = 0;
  std::int64_t p9999 = 0;
};

class LatencyHistogram {
 public:
  // max_value: largest value tracked exactly (larger ones are clamped and counted).
  // sub_bucket_bits: S, precision (relative error < 2^-S). Default: 0.8%, up to ~18 minutes in ns.
  explicit LatencyHistogram(std::int64_t max_value = std::int64_t{1} << 40, unsigned sub_bucket_bits = 7)
      : sub_bits_{sub_bucket_bits},
        half_{std::uint64_t{1} << sub_bucket_bits},
        max_value_{static_cast<std::uint64_t>(std::max<std::int64_t>(max_value, 1))},
        size_{index_of(max_value_) + 1},
        counts_{std::make_unique<std::atomic<std::uint64_t>[]>(size_)} {}

  LatencyHistogram(const LatencyHistogram&) = delete;
  LatencyHistogram& operator=(const LatencyHistogram&) = delete;

  // [snippet:index]
  // Bucket index of a value. Values below 2*half map to themselves; above,
  // e is the number of low bits dropped, so each bucket is 2^e wide while the
  // value is at least half * 2^e: relative width at most 1/half.
  [[nodiscard]] std::size_t index_of(std::uint64_t v) const noexcept {
    if (v < 2 * half_) {
      return static_cast<std::size_t>(v);
    }
    const auto e = static_cast<unsigned>(std::bit_width(v)) - (sub_bits_ + 1);
    return static_cast<std::size_t>((e + 1) * half_ + ((v >> e) - half_));
  }
  // Smallest value that maps to bucket i.
  [[nodiscard]] std::uint64_t lowest_in(std::size_t i) const noexcept {
    if (i < 2 * half_) {
      return i;
    }
    const auto e = static_cast<unsigned>(i / half_) - 1;
    return ((i % half_) + half_) << e;
  }
  // Largest value that maps to bucket i (what percentiles report).
  [[nodiscard]] std::uint64_t highest_in(std::size_t i) const noexcept {
    if (i < 2 * half_) {
      return i;
    }
    const auto e = static_cast<unsigned>(i / half_) - 1;
    return lowest_in(i) + (std::uint64_t{1} << e) - 1;
  }
  // [/snippet:index]

  // [snippet:record]
  // Single writer: plain load + store instead of fetch_add avoids a locked
  // instruction on every call; readers still see whole values.
  void record(std::int64_t value) noexcept {
    std::uint64_t v = value < 0 ? 0 : static_cast<std::uint64_t>(value);
    if (v > max_value_) {
      bump(overflows_);
      v = max_value_;
    }
    bump(counts_[index_of(v)]);
    bump(total_);
    sum_.store(sum_.load(std::memory_order_relaxed) + v, std::memory_order_relaxed);
    if (v < min_.load(std::memory_order_relaxed)) {
      min_.store(v, std::memory_order_relaxed);
    }
    if (v > max_.load(std::memory_order_relaxed)) {
      max_.store(v, std::memory_order_relaxed);
    }
  }
  // [/snippet:record]

  [[nodiscard]] std::uint64_t count() const noexcept { return total_.load(std::memory_order_relaxed); }
  [[nodiscard]] std::size_t bucket_count() const noexcept { return size_; }
  // Count in bucket i (relaxed: may trail a concurrent writer, never torn).
  [[nodiscard]] std::uint64_t count_at(std::size_t i) const noexcept {
    return i < size_ ? counts_[i].load(std::memory_order_relaxed) : 0;
  }
  [[nodiscard]] std::size_t memory_bytes() const noexcept { return size_ * sizeof(std::uint64_t); }

  // Value at or below which `percent` percent of the recorded values fall,
  // reported as the highest value equivalent to that bucket (so it never
  // under-reports), and exactly the maximum for percent >= 100.
  [[nodiscard]] std::int64_t value_at_percentile(double percent) const noexcept {
    const std::uint64_t total = count();
    if (total == 0) {
      return 0;
    }
    if (percent >= 100.0) {
      return static_cast<std::int64_t>(max_.load(std::memory_order_relaxed));
    }
    const double p = std::max(percent, 0.0);
    // Rank of the target value, 1-based: the smallest rank r with r/total >= p/100.
    // (The small epsilon keeps 99.9% of 1000 at rank 999 despite rounding in p / 100.)
    auto rank = static_cast<std::uint64_t>(std::ceil(p / 100.0 * static_cast<double>(total) - 1e-9));
    rank = std::clamp<std::uint64_t>(rank, 1, total);
    std::uint64_t seen = 0;
    for (std::size_t i = 0; i < size_; ++i) {
      seen += counts_[i].load(std::memory_order_relaxed);
      if (seen >= rank) {
        const std::uint64_t hi = std::min(highest_in(i), max_.load(std::memory_order_relaxed));
        return static_cast<std::int64_t>(hi);
      }
    }
    return static_cast<std::int64_t>(max_.load(std::memory_order_relaxed));
  }

  [[nodiscard]] LatencySummary summary() const noexcept {
    LatencySummary s;
    s.count = count();
    s.overflows = overflows_.load(std::memory_order_relaxed);
    if (s.count == 0) {
      return s;
    }
    s.min = static_cast<std::int64_t>(min_.load(std::memory_order_relaxed));
    s.max = static_cast<std::int64_t>(max_.load(std::memory_order_relaxed));
    s.mean = static_cast<double>(sum_.load(std::memory_order_relaxed)) / static_cast<double>(s.count);
    s.p50 = value_at_percentile(50.0);
    s.p90 = value_at_percentile(90.0);
    s.p99 = value_at_percentile(99.0);
    s.p999 = value_at_percentile(99.9);
    s.p9999 = value_at_percentile(99.99);
    return s;
  }

  // Adds other's counts to this one (same configuration required; returns false otherwise).
  bool merge(const LatencyHistogram& other) noexcept {
    if (other.size_ != size_ || other.sub_bits_ != sub_bits_) {
      return false;
    }
    for (std::size_t i = 0; i < size_; ++i) {
      counts_[i].fetch_add(other.counts_[i].load(std::memory_order_relaxed), std::memory_order_relaxed);
    }
    total_.fetch_add(other.count(), std::memory_order_relaxed);
    overflows_.fetch_add(other.overflows_.load(std::memory_order_relaxed), std::memory_order_relaxed);
    sum_.fetch_add(other.sum_.load(std::memory_order_relaxed), std::memory_order_relaxed);
    if (other.count() > 0) {
      min_.store(std::min(min_.load(), other.min_.load()), std::memory_order_relaxed);
      max_.store(std::max(max_.load(), other.max_.load()), std::memory_order_relaxed);
    }
    return true;
  }

  void reset() noexcept {
    for (std::size_t i = 0; i < size_; ++i) {
      counts_[i].store(0, std::memory_order_relaxed);
    }
    total_.store(0, std::memory_order_relaxed);
    overflows_.store(0, std::memory_order_relaxed);
    sum_.store(0, std::memory_order_relaxed);
    min_.store(std::numeric_limits<std::uint64_t>::max(), std::memory_order_relaxed);
    max_.store(0, std::memory_order_relaxed);
  }

 private:
  static void bump(std::atomic<std::uint64_t>& c) noexcept {
    c.store(c.load(std::memory_order_relaxed) + 1, std::memory_order_relaxed);
  }

  unsigned sub_bits_;
  std::uint64_t half_;
  std::uint64_t max_value_;
  std::size_t size_;
  std::unique_ptr<std::atomic<std::uint64_t>[]> counts_;
  std::atomic<std::uint64_t> total_{0};
  std::atomic<std::uint64_t> overflows_{0};
  std::atomic<std::uint64_t> sum_{0};
  std::atomic<std::uint64_t> min_{std::numeric_limits<std::uint64_t>::max()};
  std::atomic<std::uint64_t> max_{0};
};

}  // namespace minidaq
