// SPDX-License-Identifier: MIT
// Exercise 4.3 starter.
#include "stage_latencies.hpp"

namespace ex {

StageLatencies::StageLatencies(std::vector<std::string> names) : names_{std::move(names)} {
  for (std::size_t i = 0; i < names_.size(); ++i) {
    histograms_.push_back(std::make_unique<minidaq::LatencyHistogram>());
  }
}

std::vector<HistogramSnapshot> StageLatencies::snapshot() const {
  // TODO: copy every bucket of every stage with count_at().
  return {};
}

std::vector<IntervalStats> StageLatencies::interval(const std::vector<HistogramSnapshot>& before,
                                                    const std::vector<HistogramSnapshot>& after) const {
  // TODO: validate, subtract bucket by bucket, then walk the deltas for each percentile.
  (void)before;
  (void)after;
  return {};
}

std::string to_json(const std::vector<IntervalStats>& stats, std::int64_t interval_ns) {
  // TODO: see the exact format in the tests.
  (void)stats;
  (void)interval_ns;
  return "{}";
}

}  // namespace ex
