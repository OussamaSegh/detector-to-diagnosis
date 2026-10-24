// SPDX-License-Identifier: MIT
// MiniDAQ - counting coincidences against the simulator's ground truth (Chapter 8).
//
// A deliberately simple reference: a fixed window opened by the first single
// that is not yet part of a window, no geometry cuts, energy window applied to
// each single first. A window with exactly two singles is a coincidence and is
// classified from the truth; a window with more is a multiple. Chapter 10's
// sorter is tested against counts like these.
#pragma once

#include <cstdint>
#include <span>

#include "minidaq/sim/detector_simulator.hpp"

namespace minidaq::sim {

struct CountingWindow {
  Picoseconds width{4'000};  // a second single at most this much later
  double energy_low_kev = 0.0;
  double energy_high_kev = 1.0e9;
};

// [snippet:counts]
struct CoincidenceCounts {
  std::uint64_t singles = 0;    // inside the energy window
  std::uint64_t trues = 0;      // same decay, neither photon scattered
  std::uint64_t scatters = 0;   // same decay, at least one photon scattered
  std::uint64_t randoms = 0;    // two different decays
  std::uint64_t multiples = 0;  // windows with three or more singles

  [[nodiscard]] std::uint64_t prompts() const noexcept { return trues + scatters + randoms; }
};
// [/snippet:counts]

// `singles` must be in time order (as the simulator returns them).
[[nodiscard]] CoincidenceCounts count_coincidences(std::span<const TruthSingle> singles,
                                                   const CountingWindow& window);

}  // namespace minidaq::sim
