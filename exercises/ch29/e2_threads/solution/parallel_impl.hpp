// SPDX-License-Identifier: MIT
#pragma once

#include <algorithm>
#include <thread>
#include <vector>

namespace ex {

// [snippet:parallel_for]
template <typename Body>
void parallel_for(std::size_t count, unsigned threads, const Body& body) {
  const std::size_t t = std::clamp<std::size_t>(threads, 1, std::max<std::size_t>(count, 1));
  if (t == 1) {
    body(std::size_t{0}, count, 0U);
    return;
  }
  std::vector<std::jthread> pool;
  pool.reserve(t);
  for (std::size_t k = 0; k < t; ++k) {
    // count * k / t, not (count / t) * k: the chunks differ by at most one and the last ends at
    // count, whatever the remainder.
    const std::size_t first = count * k / t;
    const std::size_t last = count * (k + 1) / t;
    pool.emplace_back([&body, first, last, k] { body(first, last, static_cast<unsigned>(k)); });
  }
}
// [/snippet:parallel_for]

}  // namespace ex
