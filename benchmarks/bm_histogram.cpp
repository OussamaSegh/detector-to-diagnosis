// SPDX-License-Identifier: MIT
// Cost of recording one latency sample (Chapter 4), and of reading the clock.
#include <benchmark/benchmark.h>

#include <cstdint>
#include <random>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/metrics/latency_histogram.hpp"

namespace {

void BM_HistogramRecord(benchmark::State& state) {
  minidaq::LatencyHistogram h;
  std::mt19937_64 rng{1};
  std::vector<std::int64_t> values(4096);
  for (auto& v : values) {
    v = static_cast<std::int64_t>(rng() >> 40);  // 0 .. 16 M ns
  }
  std::size_t i = 0;
  for (auto _ : state) {
    h.record(values[i++ & 4095]);
  }
  benchmark::DoNotOptimize(h.count());
}

void BM_MonotonicClock(benchmark::State& state) {
  for (auto _ : state) {
    benchmark::DoNotOptimize(minidaq::monotonic_ns());
  }
}

void BM_Percentile(benchmark::State& state) {
  minidaq::LatencyHistogram h;
  std::mt19937_64 rng{1};
  for (int i = 0; i < 1'000'000; ++i) {
    h.record(static_cast<std::int64_t>(rng() >> 40));
  }
  for (auto _ : state) {
    benchmark::DoNotOptimize(h.value_at_percentile(99.9));
  }
}

}  // namespace

BENCHMARK(BM_HistogramRecord);
BENCHMARK(BM_MonotonicClock);
BENCHMARK(BM_Percentile)->Unit(benchmark::kMicrosecond);
