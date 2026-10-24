// SPDX-License-Identifier: MIT
#include "parallel_sorter.hpp"

#include <algorithm>
#include <thread>

namespace ex103 {

std::vector<std::size_t> slice_starts(std::span<const minidaq::Single> singles, const minidaq::SorterConfig& cfg,
                                      unsigned slices) {
  // TODO: equal pieces, cut wherever they fall. A window that straddles a cut
  // is split in two, and the second piece opens windows the serial sorter
  // never opened.
  (void)cfg;
  std::vector<std::size_t> starts;
  for (unsigned s = 0; s < std::max(1U, slices); ++s) {
    starts.push_back(singles.size() * s / std::max(1U, slices));
  }
  return starts;
}

std::vector<minidaq::Coincidence> sort_parallel(std::span<const minidaq::Single> singles,
                                                const minidaq::SorterConfig& cfg, unsigned threads) {
  // TODO: each slice sees only its own singles, so its last delayed windows
  // are cut short.
  const auto starts = slice_starts(singles, cfg, threads);
  std::vector<std::vector<minidaq::Coincidence>> found(starts.size());
  {
    std::vector<std::jthread> workers;
    for (std::size_t s = 0; s < starts.size(); ++s) {
      workers.emplace_back([&, s] {
        const std::size_t end = s + 1 < starts.size() ? starts[s + 1] : singles.size();
        minidaq::CoincidenceSorter sorter{cfg};
        sorter.push(singles.subspan(starts[s], end - starts[s]), found[s]);
        sorter.flush(found[s]);
      });
    }
  }
  std::vector<minidaq::Coincidence> all;
  for (auto& f : found) {
    all.insert(all.end(), f.begin(), f.end());
  }
  return all;
}

}  // namespace ex103
