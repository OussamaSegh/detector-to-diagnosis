// SPDX-License-Identifier: MIT
#include "parallel.hpp"

namespace ex {

std::vector<double> scatter_add(std::span<const std::size_t> index,
                                std::span<const double> value, std::size_t size,
                                unsigned threads) {
  std::vector<double> out(size, 0.0);
  parallel_for(index.size(), threads, [&](std::size_t first, std::size_t last, unsigned) {
    for (std::size_t i = first; i < last; ++i) {
      out[index[i]] += value[i];
    }
  });
  return out;
}

}  // namespace ex
