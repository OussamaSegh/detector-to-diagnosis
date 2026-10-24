// SPDX-License-Identifier: MIT
// Exercise 10.5: merging board streams by time slices instead of a heap.
#pragma once

#include <span>
#include <vector>

#include "minidaq/core/single.hpp"

namespace ex105 {

// Merges complete per-board streams (each in TimeOrder) into one stream, one
// time slice [T, T + slice) at a time: gather every board's singles of the
// slice, sort them, append. The result equals minidaq::StreamMerger's output
// for the same boards: time order, ties by crystal, then by board.
[[nodiscard]] std::vector<minidaq::Single> merge_by_slices(std::span<const std::vector<minidaq::Single>> boards,
                                                           minidaq::Picoseconds slice);

}  // namespace ex105
