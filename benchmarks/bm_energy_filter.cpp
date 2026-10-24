// SPDX-License-Identifier: MIT
// Energy window filter kernels (Chapter 5). Arguments:
//   kernel   0 branchy, 1 branchless, 2 avx2, 3 avx512
//   accept   percentage of singles inside the window
//   pattern  0 random energies, a different batch every iteration
//            1 sorted by energy (the branch becomes predictable)
//            2 random energies, the SAME batch every iteration: the trap. The
//              branch predictor learns the 4,096 outcomes and the branchy
//              kernel looks fast; real data never repeats like that.
//   singles  per iteration: 4,096 (one pipeline batch, 64 KiB; iterations cycle
//            through 64 such batches) or 1 Mi (16 MiB, streams from memory)
#include <benchmark/benchmark.h>

#include <algorithm>
#include <random>
#include <vector>

#include "minidaq/processing/energy_filter.hpp"

namespace {

using minidaq::FilterKernel;
using minidaq::Single;

// Energies uniform in [0, 1000) keV, so a window [500 - 5a, 500 + 5a] holds a percent.
std::vector<Single> make_input(std::size_t n, bool sorted) {
  std::mt19937_64 rng{42};
  std::uniform_real_distribution<float> e{0.0F, 1000.0F};
  std::vector<Single> v(n);
  for (std::size_t i = 0; i < v.size(); ++i) {
    v[i] = Single{minidaq::Picoseconds{static_cast<std::int64_t>(i)}, minidaq::CrystalId{0}, minidaq::KeV{e(rng)}};
  }
  if (sorted) {
    std::sort(v.begin(), v.end(), [](const Single& a, const Single& b) { return a.energy < b.energy; });
  }
  return v;
}

void BM_EnergyFilter(benchmark::State& state) {
  const auto kernel = static_cast<FilterKernel>(state.range(0));
  if (!minidaq::kernel_available(kernel)) {
    state.SkipWithError("kernel not available on this CPU");
    return;
  }
  const auto accept = static_cast<float>(state.range(1));
  const auto pattern = state.range(2);
  const auto n = static_cast<std::size_t>(state.range(3));
  const std::size_t batches = (n == 4096 && pattern != 2) ? 64 : 1;
  const auto pool = make_input(n * batches, pattern == 1);
  std::vector<Single> out(n);
  const minidaq::EnergyWindow w{minidaq::KeV{500.0F - 5.0F * accept}, minidaq::KeV{500.0F + 5.0F * accept}};
  // [snippet:loop]
  std::size_t kept = 0;
  std::size_t b = 0;
  for (auto _ : state) {
    const std::span<const Single> in{pool.data() + b * n, n};
    kept += minidaq::filter_energy(in, out, w, kernel);
    benchmark::DoNotOptimize(kept);
    benchmark::ClobberMemory();
    b = b + 1 == batches ? 0 : b + 1;  // a different batch each time
  }
  // [/snippet:loop]
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(n));
  state.counters["kept_pct"] =
      100.0 * static_cast<double>(kept) / (static_cast<double>(state.iterations()) * static_cast<double>(n));
  state.SetLabel(std::string{to_string(kernel)});
}

void args(benchmark::internal::Benchmark* b) {
  for (int n : {4096, 1 << 20}) {
    for (int pattern : {0, 1, 2}) {
      if (pattern == 2 && n != 4096) {
        continue;
      }
      for (int accept : {10, 50, 90}) {
        for (int k = 0; k <= 3; ++k) {
          b->Args({k, accept, pattern, n});
        }
      }
    }
  }
}

}  // namespace

BENCHMARK(BM_EnergyFilter)->Apply(args)->Unit(benchmark::kMicrosecond);
