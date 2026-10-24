// SPDX-License-Identifier: MIT
// Exercise 5.4 benchmark (identical in starter and solution). Argument 0: codes
// uniform over the 2,048 bins; 1: a 511 keV photopeak (normal, sigma 25 keV,
// code = 2 x keV), where many consecutive codes hit the same few bins;
// 2: a constant code, the worst case for the dependency chain.
#include <benchmark/benchmark.h>

#include <random>
#include <vector>

#include "spectrum.hpp"

namespace {

std::vector<std::uint16_t> codes(int kind) {
  std::mt19937_64 rng{5};
  std::uniform_int_distribution<int> uni{0, 2047};
  std::normal_distribution<double> peak{1022.0, 50.0};
  std::vector<std::uint16_t> v(1 << 20);
  for (auto& c : v) {
    const int x = kind == 0 ? uni(rng) : kind == 1 ? static_cast<int>(peak(rng)) : 1022;
    c = static_cast<std::uint16_t>(x < 0 ? 0 : x > 2047 ? 2047 : x);
  }
  return v;
}

template <auto Fill>
void BM_Spectrum(benchmark::State& state) {
  const auto v = codes(static_cast<int>(state.range(0)));
  ex::Spectrum h{};
  for (auto _ : state) {
    Fill(v, h);
    benchmark::DoNotOptimize(h.data());
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(v.size()));
}

}  // namespace

BENCHMARK(BM_Spectrum<ex::fill_simple>)->Arg(0)->Arg(1)->Arg(2);
BENCHMARK(BM_Spectrum<ex::fill_split>)->Arg(0)->Arg(1)->Arg(2);
