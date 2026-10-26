// SPDX-License-Identifier: MIT
// What the process's flight recorder holds (Chapter 21), for tests that check that an item
// records its events. The recorder is shared by every test of the process, so a test asks only
// for the events recorded since it began.
#pragma once

#include <time.h>

#include <cstdint>
#include <vector>

#include "minidaq/core/flight_recorder.hpp"

namespace minidaq::test_support {

// CLOCK_MONOTONIC, as the recorder stamps its events.
inline std::uint64_t trace_clock_ns() {
  timespec ts{};
  (void)clock_gettime(CLOCK_MONOTONIC, &ts);
  return static_cast<std::uint64_t>(ts.tv_sec) * 1'000'000'000U + static_cast<std::uint64_t>(ts.tv_nsec);
}

// The events with this code recorded at or after `since_ns`, oldest first.
inline std::vector<TraceEvent> traced_since(std::uint64_t since_ns, TraceCode code) {
  std::vector<TraceEvent> all(FlightRecorder::kCapacity);
  all.resize(flight_recorder().snapshot_into(all));
  std::erase_if(all, [&](const TraceEvent& e) { return e.t_ns < since_ns || e.code != code; });
  return all;
}

}  // namespace minidaq::test_support
