// SPDX-License-Identifier: MIT
// Exercise 9.3: two readout boards whose clocks drift apart, and a correction
// from periodic sync pulses.
#pragma once

#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace ex93 {

// A board's free-running clock: local = offset + (1 + ppm * 1e-6) * global.
struct BoardClock {
  double offset_ps = 0.0;
  double drift_ppm = 0.0;
  [[nodiscard]] double local_of(double global_ps) const noexcept {
    return offset_ps + (1.0 + drift_ppm * 1e-6) * global_ps;
  }
};

// What the boards record: for each true coincidence, the local time stamp on
// board A and on board B; for each sync pulse k (sent to both boards at the
// global time k * sync_period), its local time stamp on each board.
struct Recording {
  std::vector<std::pair<std::int64_t, std::int64_t>> pairs;  // (local A, local B)
  std::vector<std::int64_t> sync_a;                          // local time of sync k on A
  std::vector<std::int64_t> sync_b;
  double sync_period_ps = 0.0;
};

// Simulates `seconds` of pairs at `pair_rate_hz`, each photon time stamped
// with a Gaussian jitter of `jitter_ps`; sync pulses with `sync_jitter_ps`.
[[nodiscard]] Recording record(BoardClock a, BoardClock b, double seconds, double pair_rate_hz,
                               double sync_period_s, double jitter_ps, double sync_jitter_ps, std::uint64_t seed);

// Maps one board's local times to global time, from that board's sync stamps.
class ClockCorrection {
 public:
  ClockCorrection(std::span<const std::int64_t> sync_local, double sync_period_ps);
  // The global time of a local time stamp.
  [[nodiscard]] double to_global(std::int64_t local_ps) const;

 private:
  std::vector<std::int64_t> sync_;
  double period_ps_;
};

// The drift of B relative to A in ppm, estimated from the coincidences alone
// (no sync pulses): the slope of (tB - tA) against tA.
[[nodiscard]] double estimate_relative_drift_ppm(std::span<const std::pair<std::int64_t, std::int64_t>> pairs);

}  // namespace ex93
