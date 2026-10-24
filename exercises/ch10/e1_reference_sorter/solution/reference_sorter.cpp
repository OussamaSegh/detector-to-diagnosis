// SPDX-License-Identifier: MIT
#include "reference_sorter.hpp"

namespace ex101 {

// [snippet:sort]
std::vector<Pair> sort_coincidences(std::span<const minidaq::Single> singles, const Rules& rules) {
  // Indices of the singles inside the energy window; windows are formed over these only.
  std::vector<std::size_t> in;
  in.reserve(singles.size());
  for (std::size_t i = 0; i < singles.size(); ++i) {
    const auto e = static_cast<double>(singles[i].energy.count());
    if (e >= rules.energy_low_kev && e <= rules.energy_high_kev) {
      in.push_back(i);
    }
  }
  std::vector<Pair> out;
  std::size_t i = 0;
  while (i < in.size()) {
    const minidaq::Picoseconds open = singles[in[i]].time;
    std::size_t n = 1;
    while (i + n < in.size() && singles[in[i + n]].time - open <= rules.window) {
      ++n;
    }
    if (n == 2) {
      out.push_back(Pair{in[i], in[i + 1]});
    }
    i += n;  // every single in the window is used up, whatever the window held
  }
  return out;
}
// [/snippet:sort]

Classified classify(std::span<const minidaq::sim::TruthSingle> truth, std::span<const Pair> pairs) {
  Classified c;
  for (const Pair& p : pairs) {
    const auto& a = truth[p.first];
    const auto& b = truth[p.second];
    if (a.decay != b.decay) {
      ++c.randoms;  // two different annihilations
    } else if (a.scattered || b.scattered) {
      ++c.scatters;  // same annihilation, but at least one photon changed direction
    } else {
      ++c.trues;
    }
  }
  return c;
}

}  // namespace ex101
