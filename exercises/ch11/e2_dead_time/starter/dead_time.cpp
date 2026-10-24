// SPDX-License-Identifier: MIT
#include "dead_time.hpp"

#include "minidaq/core/geometry.hpp"

namespace ex112 {

Result apply_dead_time(std::span<const minidaq::sim::TruthSingle> in, Model model, minidaq::Picoseconds tau,
                       bool pileup) {
  using G = minidaq::ScannerGeometry;
  std::vector<minidaq::Picoseconds> last(G::num_blocks, minidaq::Picoseconds{-tau.count()});
  Result r;
  for (const auto& t : in) {
    auto& l = last[G::block_of(t.single.crystal)];
    // Busy for tau after the last event.
    const bool busy = t.single.time - l <= tau;
    if (model == Model::non_paralyzable) {
      l = t.single.time;  // every event counts as "the last event"
    }
    if (busy) {
      ++r.lost;
      if (pileup) {
        // TODO: pile-up.
      }
      continue;
    }
    if (model == Model::paralyzable) {
      l = t.single.time;
    }
    r.recorded.push_back(t);
  }
  return r;
}

double recorded_rate(Model /*model*/, double n, double /*tau_s*/) {
  return n;  // TODO: the two models
}

}  // namespace ex112
