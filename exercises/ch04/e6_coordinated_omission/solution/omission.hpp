// SPDX-License-Identifier: MIT
// Exercise 4.6: coordinated omission, measured and corrected.
#pragma once

#include <cstdint>
#include <functional>
#include <vector>

#include "minidaq/metrics/latency_histogram.hpp"

namespace ex {

struct ClosedLoopRun {
  std::vector<std::int64_t> intended;  // i * interval
  std::vector<std::int64_t> start;     // when the tester actually sent request i
  std::vector<std::int64_t> end;       // when request i completed
};

[[nodiscard]] ClosedLoopRun simulate_closed_loop(std::size_t n, std::int64_t interval_ns,
                                                 const std::function<std::int64_t(std::size_t)>& service_ns);

void record_naive(minidaq::LatencyHistogram& h, const ClosedLoopRun& run);
void record_from_intended(minidaq::LatencyHistogram& h, const ClosedLoopRun& run);
void record_corrected(minidaq::LatencyHistogram& h, std::int64_t value_ns, std::int64_t expected_interval_ns);

}  // namespace ex
