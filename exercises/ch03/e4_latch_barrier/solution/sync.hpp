// SPDX-License-Identifier: MIT
// Exercise 3.4 solution.
#pragma once

#include <atomic>
#include <barrier>
#include <cstddef>
#include <cstdint>
#include <latch>
#include <thread>
#include <vector>

namespace ex {

inline std::vector<int> start_together(int n) {
  std::vector<int> seen(static_cast<std::size_t>(n));
  std::atomic<int> arrived{0};
  std::latch ready{n};
  {
    std::vector<std::jthread> threads;
    for (int i = 0; i < n; ++i) {
      threads.emplace_back([&, i] {
        arrived.fetch_add(1, std::memory_order_relaxed);
        ready.arrive_and_wait();  // nobody passes until all n have arrived
        seen[static_cast<std::size_t>(i)] = arrived.load(std::memory_order_relaxed);
      });
    }
  }  // join
  return seen;
}

struct PhasedResult {
  std::vector<std::int64_t> totals;
  int completions = 0;
};

inline PhasedResult phased_sums(const std::vector<std::vector<std::int64_t>>& values) {
  PhasedResult r;
  if (values.empty()) {
    return r;
  }
  const std::size_t workers = values.front().size();
  r.totals.assign(values.size(), 0);
  // [snippet:barrier]
  std::vector<std::int64_t> partial(workers, 0);  // one slot per worker: no sharing within a phase
  std::size_t phase = 0;
  // The completion function runs on one thread after all workers arrive and
  // before any is released, so it may read and reset every partial safely:
  // the barrier provides the happens-before edges in both directions.
  auto complete = [&]() noexcept {
    for (auto& p : partial) {
      r.totals[phase] += p;
      p = 0;
    }
    ++r.completions;
    ++phase;
  };
  std::barrier sync{static_cast<std::ptrdiff_t>(workers), complete};
  {
    std::vector<std::jthread> threads;
    for (std::size_t w = 0; w < workers; ++w) {
      threads.emplace_back([&, w] {
        for (std::size_t p = 0; p < values.size(); ++p) {
          partial[w] += values[p][w];
          sync.arrive_and_wait();
        }
      });
    }
  }
  // [/snippet:barrier]
  return r;
}

}  // namespace ex
