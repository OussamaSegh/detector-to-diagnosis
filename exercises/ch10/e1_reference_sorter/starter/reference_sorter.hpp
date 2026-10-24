// SPDX-License-Identifier: MIT
// Exercise 10.1: a single-threaded reference sorter, checked against truth.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/sim/detector_simulator.hpp"

namespace ex101 {

// Indices of the two singles of a coincidence in the sorter's input; first < second.
struct Pair {
  std::size_t first = 0;
  std::size_t second = 0;
  friend bool operator==(const Pair&, const Pair&) = default;
};

struct Rules {
  minidaq::Picoseconds window{4'000};  // inclusive
  double energy_low_kev = 435.0;      // inclusive
  double energy_high_kev = 585.0;     // inclusive
};

// Fixed (non-paralysable) windows: the first single not yet in a window opens
// one; singles up to `window` later join it; exactly two singles make a
// coincidence, three or more are discarded. Singles outside the energy window
// take no part. `singles` is in time order.
[[nodiscard]] std::vector<Pair> sort_coincidences(std::span<const minidaq::Single> singles, const Rules& rules);

struct Classified {
  std::uint64_t trues = 0;
  std::uint64_t scatters = 0;
  std::uint64_t randoms = 0;
  friend bool operator==(const Classified&, const Classified&) = default;
};

// Classifies coincidences found in `truth[i].single` by the truth of their singles.
[[nodiscard]] Classified classify(std::span<const minidaq::sim::TruthSingle> truth, std::span<const Pair> pairs);

}  // namespace ex101
