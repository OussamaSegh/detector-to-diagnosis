// SPDX-License-Identifier: MIT
// The provided driver: the same in starter and solution.
#include "policies.hpp"

namespace ex102 {

std::vector<minidaq::Coincidence> sort_with(std::span<const minidaq::Single> singles, minidaq::Picoseconds window,
                                            minidaq::MultiplesPolicy policy, const Good& good) {
  std::vector<minidaq::Coincidence> out;
  std::size_t i = 0;
  while (i < singles.size()) {
    std::size_t n = 1;
    while (i + n < singles.size() && singles[i + n].time - singles[i].time <= window) {
      ++n;
    }
    const auto w = singles.subspan(i, n);
    if (n == 2 && good(w[0], w[1])) {
      out.push_back(minidaq::Coincidence{w[0], w[1], minidaq::CoincidenceKind::prompt});
    } else if (n > 2) {
      for (const Pair& p : resolve(w, policy, good)) {
        out.push_back(minidaq::Coincidence{w[p.first], w[p.second], minidaq::CoincidenceKind::prompt});
      }
    }
    i += n;
  }
  return out;
}

}  // namespace ex102
