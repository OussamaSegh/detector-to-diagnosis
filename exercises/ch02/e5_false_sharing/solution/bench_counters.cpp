#include <benchmark/benchmark.h>

#include "counters.hpp"

namespace {
ex::StageCounters g_counters;

void BM_StageCounters(benchmark::State& state) {
  auto& c = g_counters.stage(static_cast<std::size_t>(state.thread_index()));
  for (auto _ : state) {
    for (int i = 0; i < 100'000; ++i) {
      c.events_in.fetch_add(1, std::memory_order_relaxed);
    }
  }
  state.SetItemsProcessed(state.iterations() * 100'000);
}
}  // namespace

BENCHMARK(BM_StageCounters)->Threads(1)->Threads(2)->Threads(4)->UseRealTime();
