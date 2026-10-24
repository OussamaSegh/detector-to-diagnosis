// SPDX-License-Identifier: MIT
// Exercise 3.4 starter.
#pragma once

#include <atomic>
#include <barrier>
#include <cstdint>
#include <latch>
#include <thread>
#include <vector>

namespace ex {

inline std::vector<int> start_together(int n) {
  // TODO: n jthreads, a shared std::atomic<int> arrived, and a std::latch.
  return {};
}

struct PhasedResult {
  std::vector<std::int64_t> totals;  // one per phase
  int completions = 0;               // how many times the completion step ran
};

inline PhasedResult phased_sums(const std::vector<std::vector<std::int64_t>>& values) {
  // TODO: one jthread per worker, per-worker partial sums, a std::barrier whose
  // completion function folds the partials into totals[phase].
  return {};
}

}  // namespace ex
