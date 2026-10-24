// SPDX-License-Identifier: MIT
// False sharing (Chapter 2): two threads increment two different counters.
#include <benchmark/benchmark.h>

#include <atomic>
#include <cstdint>

#include "minidaq/core/cache.hpp"

namespace {

// [snippet:counters]
struct SharedLine {
  std::atomic<std::uint64_t> counter[2];  // 16 bytes: both in one cache line
};
struct PaddedLines {
  minidaq::CacheAligned<std::atomic<std::uint64_t>> counter[2];  // one line each
};
static_assert(sizeof(PaddedLines) == 2 * minidaq::cache_line_size);
// [/snippet:counters]

SharedLine g_shared{};
PaddedLines g_padded{};
constexpr int kIncrements = 1'000'000;

void BM_Counters_SameLine(benchmark::State& state) {
  auto& c = g_shared.counter[state.thread_index()];
  for (auto _ : state) {
    for (int i = 0; i < kIncrements; ++i) {
      c.fetch_add(1, std::memory_order_relaxed);
    }
  }
  state.SetItemsProcessed(state.iterations() * kIncrements);
}

void BM_Counters_Padded(benchmark::State& state) {
  auto& c = g_padded.counter[state.thread_index()].value;
  for (auto _ : state) {
    for (int i = 0; i < kIncrements; ++i) {
      c.fetch_add(1, std::memory_order_relaxed);
    }
  }
  state.SetItemsProcessed(state.iterations() * kIncrements);
}

}  // namespace

BENCHMARK(BM_Counters_SameLine)->Threads(1)->Threads(2)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_Counters_Padded)->Threads(1)->Threads(2)->UseRealTime()->Unit(benchmark::kMillisecond);
