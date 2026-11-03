// SPDX-License-Identifier: MIT
#pragma once

#include <thread>
#include <vector>

namespace ex {

template <typename Body>
void parallel_for(std::size_t count, unsigned threads, const Body& body) {
  const std::size_t t = threads == 0 ? 1 : threads;
  const std::size_t chunk = count / t;
  std::vector<std::jthread> pool;
  for (std::size_t k = 0; k < t; ++k) {
    const std::size_t first = chunk * k;
    const std::size_t last = chunk * (k + 1);
    pool.emplace_back([&body, first, last, k] { body(first, last, static_cast<unsigned>(k)); });
  }
}

}  // namespace ex
