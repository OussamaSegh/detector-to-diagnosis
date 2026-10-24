// SPDX-License-Identifier: MIT
#include "policies.hpp"

namespace ex102 {

std::vector<Pair> resolve(std::span<const minidaq::Single> w, minidaq::MultiplesPolicy policy, const Good& good) {
  // TODO: only kill_all is right. Every other policy keeps every pair, good or not.
  (void)good;
  if (policy == minidaq::MultiplesPolicy::kill_all) {
    return {};
  }
  std::vector<Pair> all;
  for (std::size_t i = 0; i < w.size(); ++i) {
    for (std::size_t j = i + 1; j < w.size(); ++j) {
      all.push_back(Pair{i, j});
    }
  }
  return all;
}

}  // namespace ex102
