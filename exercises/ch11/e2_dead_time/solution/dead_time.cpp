// SPDX-License-Identifier: MIT
#include "dead_time.hpp"

#include <cmath>

#include "minidaq/core/geometry.hpp"

namespace ex112 {

// [snippet:apply]
Result apply_dead_time(std::span<const minidaq::sim::TruthSingle> in, Model model, minidaq::Picoseconds tau,
                       bool pileup) {
  using G = minidaq::ScannerGeometry;
  struct Block {
    bool busy = false;
    minidaq::Picoseconds until{};  // the block is free again from this time on
    std::size_t open = 0;          // index in `recorded` of the event being recorded
  };
  std::vector<Block> blocks(G::num_blocks);
  Result r;
  r.recorded.reserve(in.size());
  for (const auto& t : in) {
    Block& b = blocks[G::block_of(t.single.crystal)];
    const minidaq::Picoseconds now = t.single.time;
    if (b.busy && now < b.until) {
      ++r.lost;
      if (pileup) {
        ++r.piled_up;
        auto& e = r.recorded[b.open].single.energy;
        e = e + t.single.energy;
      }
      if (model == Model::paralyzable) {
        b.until = now + tau;  // the lost event restarts the dead time
      }
      continue;
    }
    b.busy = true;
    b.until = now + tau;
    b.open = r.recorded.size();
    r.recorded.push_back(t);
  }
  return r;
}
// [/snippet:apply]

double recorded_rate(Model model, double n, double tau_s) {
  return model == Model::non_paralyzable ? n / (1.0 + n * tau_s) : n * std::exp(-n * tau_s);
}

}  // namespace ex112
