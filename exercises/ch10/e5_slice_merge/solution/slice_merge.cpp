// SPDX-License-Identifier: MIT
#include "slice_merge.hpp"

#include <algorithm>
#include <limits>

#include "minidaq/pipeline/acquisition_pipeline.hpp"

namespace ex105 {

// [snippet:slices]
std::vector<minidaq::Single> merge_by_slices(std::span<const std::vector<minidaq::Single>> boards,
                                             minidaq::Picoseconds slice) {
  std::vector<minidaq::Single> out;
  std::size_t total = 0;
  minidaq::Picoseconds first{std::numeric_limits<std::int64_t>::max()};
  for (const auto& b : boards) {
    total += b.size();
    if (!b.empty()) {
      first = std::min(first, b.front().time);
    }
  }
  out.reserve(total);
  std::vector<std::size_t> pos(boards.size(), 0);
  for (minidaq::Picoseconds t = first; out.size() < total; t += slice) {
    const minidaq::Picoseconds end = t + slice;  // the slice is [t, end): each single in exactly one
    const std::size_t begin = out.size();
    for (std::size_t b = 0; b < boards.size(); ++b) {  // in board order, for the tie rule
      while (pos[b] < boards[b].size() && boards[b][pos[b]].time < end) {
        out.push_back(boards[b][pos[b]++]);
      }
    }
    // Stable: equal singles keep board order, as the heap merger's tie rule does.
    std::stable_sort(out.begin() + static_cast<std::ptrdiff_t>(begin), out.end(), minidaq::TimeOrder{});
  }
  return out;
}
// [/snippet:slices]

}  // namespace ex105
