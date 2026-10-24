#include <benchmark/benchmark.h>

#include <vector>

#include "layout.hpp"

namespace {
std::vector<ex::Single>& aos(std::size_t n) {
  static std::vector<ex::Single> v;
  if (v.size() != n) {
    v.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
      v[i] = ex::Single{static_cast<std::int64_t>(i) * 33, static_cast<std::uint32_t>(i % 18432),
                        450.0F + static_cast<float>(i % 128)};
    }
  }
  return v;
}

void BM_AoS(benchmark::State& state) {
  const auto& v = aos(static_cast<std::size_t>(state.range(0)));
  for (auto _ : state) {
    benchmark::DoNotOptimize(ex::sum_energy(v));
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
}

void BM_SoA(benchmark::State& state) {
  static const ex::SinglesSoA soa = ex::to_soa(aos(static_cast<std::size_t>(state.range(0))));
  for (auto _ : state) {
    benchmark::DoNotOptimize(ex::sum_energy(soa));
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
}
}  // namespace

BENCHMARK(BM_AoS)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
BENCHMARK(BM_SoA)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
