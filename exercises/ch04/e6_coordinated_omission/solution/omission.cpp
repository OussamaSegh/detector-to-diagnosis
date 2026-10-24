// SPDX-License-Identifier: MIT
// Exercise 4.6 solution.
#include "omission.hpp"

#include <algorithm>

namespace ex {

ClosedLoopRun simulate_closed_loop(std::size_t n, std::int64_t interval_ns,
                                   const std::function<std::int64_t(std::size_t)>& service_ns) {
  ClosedLoopRun r;
  r.intended.resize(n);
  r.start.resize(n);
  r.end.resize(n);
  std::int64_t prev_end = 0;
  for (std::size_t i = 0; i < n; ++i) {
    r.intended[i] = static_cast<std::int64_t>(i) * interval_ns;
    r.start[i] = std::max(r.intended[i], prev_end);  // the tester waits: coordination
    r.end[i] = r.start[i] + service_ns(i);
    prev_end = r.end[i];
  }
  return r;
}

void record_naive(minidaq::LatencyHistogram& h, const ClosedLoopRun& run) {
  for (std::size_t i = 0; i < run.end.size(); ++i) {
    h.record(run.end[i] - run.start[i]);
  }
}

void record_from_intended(minidaq::LatencyHistogram& h, const ClosedLoopRun& run) {
  for (std::size_t i = 0; i < run.end.size(); ++i) {
    h.record(run.end[i] - run.intended[i]);
  }
}

// [snippet:corrected]
void record_corrected(minidaq::LatencyHistogram& h, std::int64_t value_ns, std::int64_t expected_interval_ns) {
  h.record(value_ns);
  if (expected_interval_ns <= 0) {
    return;
  }
  // The requests the tester did not send while it waited would have seen
  // latencies decreasing by one interval each.
  for (std::int64_t missing = value_ns - expected_interval_ns; missing > expected_interval_ns;
       missing -= expected_interval_ns) {
    h.record(missing);
  }
}
// [/snippet:corrected]

}  // namespace ex
