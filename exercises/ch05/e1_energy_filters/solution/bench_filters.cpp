// SPDX-License-Identifier: MIT
// Exercise 5.1 benchmark (identical in starter and solution): 100 M singles (EX_SINGLES to change), three kernels,
// acceptance 10/50/90 percent, energies in random (0) or sorted (1) order.
#include <benchmark/benchmark.h>

#include <algorithm>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

#include "filters.hpp"

namespace {

std::size_t count() {
  const char* env = std::getenv("EX_SINGLES");
  return env != nullptr ? std::stoul(env) : 100'000'000UL;
}

const std::vector<ex::Single>& input(bool sorted) {
  static std::vector<ex::Single> data[2];
  auto& v = data[sorted ? 1 : 0];
  if (v.empty()) {
    std::mt19937_64 rng{42};
    std::uniform_real_distribution<float> e{0.0F, 1000.0F};
    v.resize(count());
    for (auto& s : v) {
      s.energy = minidaq::KeV{e(rng)};
    }
    if (sorted) {
      std::sort(v.begin(), v.end(), [](const ex::Single& a, const ex::Single& b) { return a.energy < b.energy; });
    }
  }
  return v;
}

template <auto Kernel>
void BM_Filter(benchmark::State& state) {
  const auto& in = input(state.range(1) == 1);
  static std::vector<ex::Single> out;
  out.resize(in.size());
  const auto a = static_cast<float>(state.range(0));
  std::size_t kept = 0;
  for (auto _ : state) {
    kept = Kernel(in, out, 500.0F - 5.0F * a, 500.0F + 5.0F * a);
    benchmark::DoNotOptimize(kept);
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(in.size()));
  state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(in.size() + kept) *
                          static_cast<std::int64_t>(sizeof(ex::Single)));
}

void args(benchmark::internal::Benchmark* b) {
  for (int order : {0, 1}) {
    for (int a : {10, 50, 90}) {
      b->Args({a, order});
    }
  }
  b->Unit(benchmark::kMillisecond);
}

}  // namespace

BENCHMARK(BM_Filter<ex::filter_branchy>)->Apply(args);
BENCHMARK(BM_Filter<ex::filter_branchless>)->Apply(args);
BENCHMARK(BM_Filter<ex::filter_simd>)->Apply(args);
