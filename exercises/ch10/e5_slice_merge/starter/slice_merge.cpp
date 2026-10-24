// SPDX-License-Identifier: MIT
#include "slice_merge.hpp"

#include <algorithm>
#include <limits>

#include "minidaq/pipeline/acquisition_pipeline.hpp"

namespace ex105 {

std::vector<minidaq::Single> merge_by_slices(std::span<const std::vector<minidaq::Single>> boards,
                                             minidaq::Picoseconds slice) {
  // TODO: two bugs at the edges of the slices, and one in the tie rule.
  std::vector<minidaq::Single> out;
  minidaq::Picoseconds first{std::numeric_limits<std::int64_t>::max()};
  minidaq::Picoseconds last{std::numeric_limits<std::int64_t>::min()};
  for (const auto& b : boards) {
    if (!b.empty()) {
      first = std::min(first, b.front().time);
      last = std::max(last, b.back().time);
    }
  }
  for (minidaq::Picoseconds t = first; t + slice <= last; t += slice) {
    const std::size_t begin = out.size();
    for (const auto& b : boards) {
      for (const minidaq::Single& s : b) {
        if (s.time >= t && s.time <= t + slice) {
          out.push_back(s);
        }
      }
    }
    std::sort(out.begin() + static_cast<std::ptrdiff_t>(begin), out.end(), minidaq::TimeOrder{});
  }
  return out;
}

}  // namespace ex105
