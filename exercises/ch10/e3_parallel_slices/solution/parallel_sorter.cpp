// SPDX-License-Identifier: MIT
#include "parallel_sorter.hpp"

#include <algorithm>
#include <thread>

namespace ex103 {

namespace {
bool in_energy(const minidaq::Single& s, const minidaq::SorterConfig& c) {
  const auto e = static_cast<double>(s.energy.count());
  return e >= c.energy_low_kev && e <= c.energy_high_kev;
}
}  // namespace

// [snippet:cuts]
std::vector<std::size_t> slice_starts(std::span<const minidaq::Single> singles, const minidaq::SorterConfig& cfg,
                                      unsigned slices) {
  // A fixed window's state carries over from single to single, but only
  // while accepted singles follow each other within the window: after a gap
  // wider than the window, the next accepted single always opens a new
  // window. Cutting there gives every slice the same windows as one sorter.
  // Rejected singles do not count: the gap is measured between accepted ones.
  std::vector<std::size_t> starts{0};
  const std::size_t n = singles.size();
  std::size_t prev = n;  // last accepted single before the candidate cut
  std::size_t next_nominal = n / std::max(1U, slices);
  for (std::size_t i = 0; i < n && starts.size() < slices; ++i) {
    if (!in_energy(singles[i], cfg)) {
      continue;
    }
    if (i >= next_nominal && prev != n && singles[i].time - singles[prev].time > cfg.window) {
      starts.push_back(i);
      next_nominal = i + n / slices;
    }
    prev = i;
  }
  return starts;
}
// [/snippet:cuts]

// [snippet:parallel]
std::vector<minidaq::Coincidence> sort_parallel(std::span<const minidaq::Single> singles,
                                                const minidaq::SorterConfig& cfg, unsigned threads) {
  const auto starts = slice_starts(singles, cfg, std::max(1U, threads));
  const std::size_t k = starts.size();
  std::vector<std::vector<minidaq::Coincidence>> found(k);
  {
    std::vector<std::jthread> workers;
    for (std::size_t s = 0; s < k; ++s) {
      workers.emplace_back([&, s] {
        const std::size_t begin = starts[s];
        const std::size_t end = s + 1 < k ? starts[s + 1] : singles.size();
        // Read ahead past the slice: the delayed windows of its last openers
        // reach up to delay + window beyond the last opener.
        std::size_t ahead = end;
        if (end > begin && cfg.delay > minidaq::Picoseconds{0}) {
          const minidaq::Picoseconds limit = singles[end - 1].time + cfg.delay + cfg.window;
          while (ahead < singles.size() && singles[ahead].time <= limit) {
            ++ahead;
          }
        }
        minidaq::CoincidenceSorter sorter{cfg};
        std::vector<minidaq::Coincidence>& out = found[s];
        sorter.push(singles.subspan(begin, ahead - begin), out);
        sorter.flush(out);
        if (end < singles.size()) {
          // Windows opened in the read-ahead belong to the next slice.
          const minidaq::Picoseconds next = singles[end].time;
          std::erase_if(out, [&](const minidaq::Coincidence& c) { return c.first.time >= next; });
        }
      });
    }
  }  // the jthreads join here
  std::vector<minidaq::Coincidence> all;
  for (auto& f : found) {
    all.insert(all.end(), f.begin(), f.end());
  }
  return all;
}
// [/snippet:parallel]

}  // namespace ex103
