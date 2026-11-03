// SPDX-License-Identifier: MIT
#include "parallel.hpp"

#include <algorithm>
#include <functional>
#include <stdexcept>
#include <string>

namespace ex {

// [snippet:scatter_add]
std::vector<double> scatter_add(std::span<const std::size_t> index,
                                std::span<const double> value, std::size_t size,
                                unsigned threads) {
  if (index.size() != value.size()) {
    throw std::invalid_argument("scatter_add: index and value differ in length");
  }
  for (const std::size_t i : index) {
    if (i >= size) {
      throw std::out_of_range("scatter_add: index " + std::to_string(i) + " of " +
                              std::to_string(size));
    }
  }
  const std::size_t t = std::clamp<std::size_t>(threads, 1, std::max<std::size_t>(index.size(), 1));
  // Two items may add to the same output: each thread adds into its own copy, and the copies
  // are summed in thread order afterwards, so no two threads write the same memory.
  std::vector<std::vector<double>> partial(t, std::vector<double>(size, 0.0));
  parallel_for(index.size(), static_cast<unsigned>(t),
               [&](std::size_t first, std::size_t last, unsigned thread) {
                 std::vector<double>& mine = partial[thread];
                 for (std::size_t i = first; i < last; ++i) {
                   mine[index[i]] += value[i];
                 }
               });
  std::vector<double> out(size, 0.0);
  for (const auto& p : partial) {
    std::transform(out.begin(), out.end(), p.begin(), out.begin(), std::plus<>());
  }
  return out;
}
// [/snippet:scatter_add]

}  // namespace ex
