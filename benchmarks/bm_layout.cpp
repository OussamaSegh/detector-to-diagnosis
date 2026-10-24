// SPDX-License-Identifier: MIT
// AoS vs SoA (Chapter 2). Sums energies over N singles stored either as an
// array of 16-byte Single structs or as separate arrays per field.
#include <benchmark/benchmark.h>

#include <cstdint>
#include <random>
#include <vector>

#include "minidaq/core/single.hpp"

using namespace minidaq;

namespace {

struct SinglesSoA {
  std::vector<std::int64_t> time_ps;
  std::vector<std::uint32_t> crystal;
  std::vector<float> energy_kev;
};

// [snippet:data]
const std::vector<Single>& aos_data(std::size_t n) {
  static std::vector<Single> v;
  if (v.size() != n) {
    std::mt19937 rng{1};
    std::normal_distribution<float> e{511.0F, 25.0F};
    v.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
      v[i] = Single{Picoseconds{static_cast<std::int64_t>(i) * 33}, CrystalId{static_cast<std::uint32_t>(i % 18432)},
                    KeV{e(rng)}};
    }
  }
  return v;
}

const SinglesSoA& soa_data(std::size_t n) {
  static SinglesSoA s;
  if (s.energy_kev.size() != n) {
    const auto& a = aos_data(n);
    s.time_ps.resize(n);
    s.crystal.resize(n);
    s.energy_kev.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
      s.time_ps[i] = a[i].time.count();
      s.crystal[i] = a[i].crystal.value();
      s.energy_kev[i] = a[i].energy.count();
    }
  }
  return s;
}
// [/snippet:data]

// [snippet:sum]
void BM_SumEnergy_AoS(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  const auto& v = aos_data(n);
  for (auto _ : state) {
    double sum = 0.0;
    for (const Single& s : v) {
      sum += static_cast<double>(s.energy.count());
    }
    benchmark::DoNotOptimize(sum);
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
  state.SetBytesProcessed(state.iterations() * state.range(0) * static_cast<std::int64_t>(sizeof(Single)));
}

void BM_SumEnergy_SoA(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  const auto& s = soa_data(n);
  for (auto _ : state) {
    double sum = 0.0;
    for (const float e : s.energy_kev) {
      sum += static_cast<double>(e);
    }
    benchmark::DoNotOptimize(sum);
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
  state.SetBytesProcessed(state.iterations() * state.range(0) * static_cast<std::int64_t>(sizeof(float)));
}
// [/snippet:sum]

// A filter that needs every field: the SoA advantage should mostly vanish.
void BM_GateAllFields_AoS(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  const auto& v = aos_data(n);
  for (auto _ : state) {
    std::uint64_t kept = 0;
    for (const Single& s : v) {
      kept += static_cast<std::uint64_t>(s.energy.count() > 435.0F && s.energy.count() < 587.0F &&
                                         s.crystal.value() < 9216U && (s.time.count() & 1) == 0);
    }
    benchmark::DoNotOptimize(kept);
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
}

void BM_GateAllFields_SoA(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  const auto& s = soa_data(n);
  for (auto _ : state) {
    std::uint64_t kept = 0;
    for (std::size_t i = 0; i < n; ++i) {
      const float e = s.energy_kev[i];
      kept += static_cast<std::uint64_t>(e > 435.0F && e < 587.0F && s.crystal[i] < 9216U && (s.time_ps[i] & 1) == 0);
    }
    benchmark::DoNotOptimize(kept);
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
}

}  // namespace

// 64 Ki singles fit in L2; 100 M singles (1.6 GB as AoS) come from DRAM.
BENCHMARK(BM_SumEnergy_AoS)->Arg(1 << 16)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
BENCHMARK(BM_SumEnergy_SoA)->Arg(1 << 16)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
BENCHMARK(BM_GateAllFields_AoS)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
BENCHMARK(BM_GateAllFields_SoA)->Arg(100'000'000)->Unit(benchmark::kMillisecond);
