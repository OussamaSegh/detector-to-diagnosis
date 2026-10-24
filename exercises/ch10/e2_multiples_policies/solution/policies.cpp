// SPDX-License-Identifier: MIT
#include "policies.hpp"

namespace ex102 {

// [snippet:resolve]
std::vector<Pair> resolve(std::span<const minidaq::Single> w, minidaq::MultiplesPolicy policy, const Good& good) {
  using minidaq::MultiplesPolicy;
  std::vector<Pair> goods;
  for (std::size_t i = 0; i < w.size(); ++i) {
    for (std::size_t j = i + 1; j < w.size(); ++j) {
      if (good(w[i], w[j])) {
        goods.push_back(Pair{i, j});
      }
    }
  }
  switch (policy) {
    case MultiplesPolicy::kill_all:
      return {};
    case MultiplesPolicy::take_all_goods:
      return goods;
    case MultiplesPolicy::keep_if_only_one_good:
      return goods.size() == 1 ? goods : std::vector<Pair>{};
    case MultiplesPolicy::take_winner_of_goods:
      break;
  }
  if (goods.empty()) {
    return {};
  }
  Pair best = goods.front();
  float best_sum = w[best.first].energy.count() + w[best.second].energy.count();
  for (const Pair& p : goods) {
    const float sum = w[p.first].energy.count() + w[p.second].energy.count();
    if (sum > best_sum) {  // strictly greater: a tie keeps the earlier pair
      best = p;
      best_sum = sum;
    }
  }
  return {best};
}
// [/snippet:resolve]

}  // namespace ex102
