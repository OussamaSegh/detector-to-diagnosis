// SPDX-License-Identifier: MIT
#include "minidaq/sim/truth_counter.hpp"

#include <vector>

namespace minidaq::sim {

CoincidenceCounts count_coincidences(std::span<const TruthSingle> singles, const CountingWindow& window) {
  std::vector<const TruthSingle*> in;
  in.reserve(singles.size());
  for (const auto& s : singles) {
    const auto e = static_cast<double>(s.single.energy.count());
    if (e >= window.energy_low_kev && e <= window.energy_high_kev) {
      in.push_back(&s);
    }
  }

  CoincidenceCounts c;
  c.singles = in.size();
  // [snippet:window]
  std::size_t i = 0;
  while (i < in.size()) {
    std::size_t n = 1;
    while (i + n < in.size() && in[i + n]->single.time - in[i]->single.time <= window.width) {
      ++n;
    }
    if (n == 2) {
      const TruthSingle& a = *in[i];
      const TruthSingle& b = *in[i + 1];
      if (a.decay != b.decay) {
        ++c.randoms;
      } else if (a.scattered || b.scattered) {
        ++c.scatters;
      } else {
        ++c.trues;
      }
    } else if (n > 2) {
      ++c.multiples;
    }
    i += n;  // the window's singles are used up: a non-paralysable window
  }
  // [/snippet:window]
  return c;
}

}  // namespace minidaq::sim
