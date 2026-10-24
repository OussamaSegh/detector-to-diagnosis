// SPDX-License-Identifier: MIT
// Exercise 10.3: sorting coincidences on several threads, by time slices.
#pragma once

#include <cstddef>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"

namespace ex103 {

// Same result as one minidaq::CoincidenceSorter over all of `singles` (pushed
// in one piece, then flushed), computed by up to `threads` sorters on
// separate threads. `singles` is in time order; cfg.mode is fixed.
[[nodiscard]] std::vector<minidaq::Coincidence> sort_parallel(std::span<const minidaq::Single> singles,
                                                              const minidaq::SorterConfig& cfg, unsigned threads);

// Where the slices start (indices into `singles`; the first is 0). Exposed so
// that the tests can check the cut rule. At most `slices` entries.
[[nodiscard]] std::vector<std::size_t> slice_starts(std::span<const minidaq::Single> singles,
                                                    const minidaq::SorterConfig& cfg, unsigned slices);

}  // namespace ex103
