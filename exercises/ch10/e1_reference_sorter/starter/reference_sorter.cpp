// SPDX-License-Identifier: MIT
#include "reference_sorter.hpp"

namespace ex101 {

std::vector<Pair> sort_coincidences(std::span<const minidaq::Single> singles, const Rules& rules) {
  // TODO: this pairs every single with the next one if it is close enough.
  // What happens to the third single of a window? Which single opens the next
  // window? Where is the energy window?
  std::vector<Pair> out;
  for (std::size_t i = 0; i + 1 < singles.size(); ++i) {
    if (singles[i + 1].time - singles[i].time <= rules.window) {
      out.push_back(Pair{i, i + 1});
    }
  }
  return out;
}

Classified classify(std::span<const minidaq::sim::TruthSingle> truth, std::span<const Pair> pairs) {
  // TODO: use the truth of both singles.
  (void)truth;
  Classified c;
  c.trues = pairs.size();
  return c;
}

}  // namespace ex101
