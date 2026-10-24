// SPDX-License-Identifier: MIT
// Exercise 4.3 starter: per-stage latency histograms with interval queries.
#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "minidaq/metrics/latency_histogram.hpp"

namespace ex {

struct HistogramSnapshot {
  std::vector<std::uint64_t> counts;  // one entry per bucket
};

struct IntervalStats {
  std::string stage;
  std::uint64_t count = 0;
  std::int64_t p50_ns = 0;
  std::int64_t p99_ns = 0;
  std::int64_t p999_ns = 0;
  std::int64_t max_ns = 0;
};

class StageLatencies {
 public:
  explicit StageLatencies(std::vector<std::string> names);

  // Hot path: only stage `stage`'s thread calls this.
  void record(std::size_t stage, std::int64_t ns) noexcept { histograms_[stage]->record(ns); }

  // Any thread, any time.
  [[nodiscard]] std::vector<HistogramSnapshot> snapshot() const;
  [[nodiscard]] std::vector<IntervalStats> interval(const std::vector<HistogramSnapshot>& before,
                                                    const std::vector<HistogramSnapshot>& after) const;

  [[nodiscard]] std::size_t size() const noexcept { return names_.size(); }
  [[nodiscard]] const minidaq::LatencyHistogram& histogram(std::size_t stage) const { return *histograms_[stage]; }

 private:
  std::vector<std::string> names_;
  std::vector<std::unique_ptr<minidaq::LatencyHistogram>> histograms_;
};

[[nodiscard]] std::string to_json(const std::vector<IntervalStats>& stats, std::int64_t interval_ns);

}  // namespace ex
