// SPDX-License-Identifier: MIT
// Exercise 10.2: multiples policies.
#pragma once

#include <cstddef>
#include <functional>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"

namespace ex102 {

// Indices into the window, first < second.
struct Pair {
  std::size_t first = 0;
  std::size_t second = 0;
  friend bool operator==(const Pair&, const Pair&) = default;
};

using Good = std::function<bool(const minidaq::Single&, const minidaq::Single&)>;

// Resolves one window of three or more singles (in time order) under `policy`.
// The candidate pairs are all pairs (i, j), i < j, considered in the order
// (0,1), (0,2), ..., (1,2), ...; "good" pairs pass `good`. The winner is the
// good pair with the highest summed energy; on a tie, the first one.
[[nodiscard]] std::vector<Pair> resolve(std::span<const minidaq::Single> window, minidaq::MultiplesPolicy policy,
                                        const Good& good);

// Provided (no need to change it): fixed windows over time-ordered singles that
// are already inside the energy window. Two singles: kept if good. Three or
// more: resolve(). Returns the coincidences found.
[[nodiscard]] std::vector<minidaq::Coincidence> sort_with(std::span<const minidaq::Single> singles,
                                                          minidaq::Picoseconds window,
                                                          minidaq::MultiplesPolicy policy, const Good& good);

}  // namespace ex102
