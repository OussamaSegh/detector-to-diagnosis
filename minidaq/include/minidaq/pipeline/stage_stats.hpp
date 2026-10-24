// SPDX-License-Identifier: MIT
// MiniDAQ - per-stage counters (Chapters 3 and 6).
//
// Each stage writes only its own StageStats (single writer), so relaxed atomic
// increments are enough: other threads (the control API) read them for
// monitoring and need no ordering with the data. One cache line per stage
// avoids false sharing between stages (Chapter 2).
#pragma once

#include <atomic>
#include <cstdint>
#include <string_view>

#include "minidaq/core/cache.hpp"

namespace minidaq {

struct alignas(cache_line_size) StageStats {
  std::atomic<std::uint64_t> items_in{0};
  std::atomic<std::uint64_t> items_out{0};
  std::atomic<std::uint64_t> batches{0};
  std::atomic<std::uint64_t> items_dropped{0};   // lost because the output was full (drop policy)
  std::atomic<std::uint64_t> items_filtered{0};  // removed by the stage's own logic (invalid, unpaired)
  std::atomic<std::uint64_t> output_stalls{0};   // times we waited for an empty output batch
  std::atomic<std::uint64_t> input_idle{0};      // times we polled an empty input

  static void add(std::atomic<std::uint64_t>& c, std::uint64_t n) noexcept {
    // Single writer: a relaxed load+store would also do; fetch_add keeps it obvious.
    c.fetch_add(n, std::memory_order_relaxed);
  }
};

// Plain copy for reporting.
struct StageSnapshot {
  std::string_view name;
  std::uint64_t items_in;
  std::uint64_t items_out;
  std::uint64_t batches;
  std::uint64_t items_dropped;
  std::uint64_t items_filtered;
  std::uint64_t output_stalls;
  std::uint64_t input_idle;
};

[[nodiscard]] inline StageSnapshot snapshot(std::string_view name, const StageStats& s) noexcept {
  return {name,
          s.items_in.load(std::memory_order_relaxed),
          s.items_out.load(std::memory_order_relaxed),
          s.batches.load(std::memory_order_relaxed),
          s.items_dropped.load(std::memory_order_relaxed),
          s.items_filtered.load(std::memory_order_relaxed),
          s.output_stalls.load(std::memory_order_relaxed),
          s.input_idle.load(std::memory_order_relaxed)};
}

}  // namespace minidaq
