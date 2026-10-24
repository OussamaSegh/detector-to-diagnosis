// SPDX-License-Identifier: MIT
// MiniDAQ - dead time and pile-up in the detector front end (Chapter 11).
//
// The detector simulator of Chapter 8 records every photon that deposits
// enough energy, however close in time to the previous one. A real channel
// cannot: after an event it is busy for a time tau (integrating the pulse,
// digitizing, transferring), and a second photon in that time is lost or, if
// its light adds to the pulse being integrated, piles up with the first.
//
// DeadTime is a stage applied to the simulator's time-ordered singles. Each
// readout unit (a block, or a single crystal) is modelled on its own:
//   - non-paralyzable: busy for tau after each recorded event; events that
//     arrive while busy are lost and do not extend the busy time.
//   - paralyzable: every event, recorded or not, makes the unit busy for tau
//     from its arrival; a fast enough stream keeps the unit busy for ever.
//   - pile-up (with either model): a lost event's energy is added to the
//     event being recorded, which may push it out of the energy window.
// For a Poisson stream of true rate n on one unit, the recorded rate m is
//   non-paralyzable: m = n / (1 + n tau)       paralyzable: m = n exp(-n tau)
// (Knoll, Radiation Detection and Measurement, chapter 4).
//
// It is a teaching model (assumption: confirm with team which parts of the
// NeuroLF front end have dead time, how long, and of which kind).
#pragma once

#include <cstdint>
#include <deque>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/sim/detector_simulator.hpp"

namespace minidaq::sim {

// [snippet:config]
enum class DeadTimeModel : std::uint8_t { none, non_paralyzable, paralyzable };
enum class DeadTimeUnit : std::uint8_t { block, crystal };  // what shares one dead time

struct DeadTimeConfig {
  DeadTimeModel model = DeadTimeModel::none;
  DeadTimeUnit unit = DeadTimeUnit::block;
  Picoseconds tau{0};
  bool pileup = false;  // add lost events' energy to the event being recorded
};

struct DeadTimeStats {
  std::uint64_t singles_in = 0;
  std::uint64_t recorded = 0;
  std::uint64_t lost = 0;       // arrived while their unit was busy
  std::uint64_t piled_up = 0;   // of the lost: energy added to a recorded event
  friend bool operator==(const DeadTimeStats&, const DeadTimeStats&) = default;
};
// [/snippet:config]

[[nodiscard]] std::string_view to_string(DeadTimeModel m) noexcept;
[[nodiscard]] Expected<DeadTimeModel, std::string> parse_dead_time_model(std::string_view s);
[[nodiscard]] Expected<DeadTimeConfig, std::string> validate(const DeadTimeConfig& cfg);

// Recorded rate for a Poisson stream of true rate n (per second) on one unit.
[[nodiscard]] double recorded_rate(DeadTimeModel m, double n, double tau_s) noexcept;
// The true rate that gives recorded rate m: the inverse of recorded_rate. A
// paralyzable unit records at most 1 / (e tau), reached at n = 1 / tau, and
// every lower recorded rate has two true rates; this returns the lower one
// (the side a scanner is normally operated on) and NaN above the maximum.
[[nodiscard]] double true_rate(DeadTimeModel m, double recorded, double tau_s) noexcept;

class DeadTime {
 public:
  // Throws std::invalid_argument if validate(cfg) fails.
  explicit DeadTime(const DeadTimeConfig& cfg);

  // `in` must be in time order (as the simulator delivers it). Appends the
  // recorded singles to `out`, in time order. An event is held back until its
  // unit has been idle for tau, since pile-up can still change its energy.
  void push(std::span<const TruthSingle> in, std::vector<TruthSingle>& out);
  // End of the stream: releases the events still held.
  void flush(std::vector<TruthSingle>& out);

  [[nodiscard]] const DeadTimeStats& stats() const noexcept { return stats_; }
  [[nodiscard]] const DeadTimeConfig& config() const noexcept { return cfg_; }

 private:
  struct Unit {
    bool busy = false;
    Picoseconds busy_until{};
    std::uint64_t open = 0;  // sequence number of the event being recorded
  };
  [[nodiscard]] std::size_t unit_of(const Single& s) const noexcept;
  void release_until(Picoseconds now, std::vector<TruthSingle>& out);

  DeadTimeConfig cfg_;
  std::vector<Unit> units_;
  // Recorded events not yet released, in arrival (time) order. held_[0] has
  // sequence number first_seq_.
  std::deque<TruthSingle> held_;
  std::deque<Picoseconds> held_until_;  // when each held event's unit became free, as known so far
  std::uint64_t first_seq_ = 0;
  DeadTimeStats stats_{};
};

}  // namespace minidaq::sim
