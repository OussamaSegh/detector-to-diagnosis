// SPDX-License-Identifier: MIT
// Exercise 5.2 benchmark (identical in starter and solution): singles per second.
#include <benchmark/benchmark.h>

#include <vector>

#include "event_source.hpp"

static void BM_EventSource(benchmark::State& state) {
  ex::EventSource src{{}};
  std::vector<ex::Single> v(4096);
  for (auto _ : state) {
    src.generate(v);
    benchmark::DoNotOptimize(v.data());
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(v.size()));
}
BENCHMARK(BM_EventSource);
