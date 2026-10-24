// SPDX-License-Identifier: MIT
// Exercise 11.2: dead time and pile-up in a block detector.
#pragma once

#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/sim/detector_simulator.hpp"

namespace ex112 {

enum class Model : std::uint8_t {
  non_paralyzable,  // busy for tau after each RECORDED event
  paralyzable,      // busy for tau after EVERY event, recorded or not
};

struct Result {
  std::vector<minidaq::sim::TruthSingle> recorded;  // in time order
  std::uint64_t lost = 0;                           // arrived while their block was busy
  std::uint64_t piled_up = 0;                       // of the lost: energy added to the recorded event
};

// One dead time per block (minidaq::ScannerGeometry::block_of). `in` is in
// time order; tau > 0. An event that arrives exactly tau after the start of
// the dead time is recorded. With `pileup`, a lost event's energy is added to
// the event its block is recording.
[[nodiscard]] Result apply_dead_time(std::span<const minidaq::sim::TruthSingle> in, Model model,
                                     minidaq::Picoseconds tau, bool pileup);

// Recorded rate on one unit for a Poisson stream of true rate n per second.
[[nodiscard]] double recorded_rate(Model model, double n, double tau_s);

}  // namespace ex112
