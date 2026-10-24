// SPDX-License-Identifier: MIT
// Exercise 4.6 starter.
#include "omission.hpp"

namespace ex {

ClosedLoopRun simulate_closed_loop(std::size_t n, std::int64_t interval_ns,
                                   const std::function<std::int64_t(std::size_t)>& service_ns) {
  // TODO: start[i] = max(i * interval, end[i - 1]); end[i] = start[i] + service_ns(i).
  (void)n;
  (void)interval_ns;
  (void)service_ns;
  return {};
}

void record_naive(minidaq::LatencyHistogram& h, const ClosedLoopRun& run) {
  // TODO
  (void)h;
  (void)run;
}

void record_from_intended(minidaq::LatencyHistogram& h, const ClosedLoopRun& run) {
  // TODO
  (void)h;
  (void)run;
}

void record_corrected(minidaq::LatencyHistogram& h, std::int64_t value_ns, std::int64_t expected_interval_ns) {
  // TODO: record value, then value - k * interval while it stays above the interval.
  (void)expected_interval_ns;
  h.record(value_ns);
}

}  // namespace ex
