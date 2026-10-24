// SPDX-License-Identifier: MIT
// Throughput of the MDQ-P1 stream decoder (Chapter 2 milestone).
#include <benchmark/benchmark.h>

#include <cstdint>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

using namespace minidaq;

static void BM_DecodePacked(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  std::vector<std::uint64_t> words(n);
  for (std::size_t i = 0; i < n; ++i) {
    words[i] = packed::pack({static_cast<std::uint32_t>((i * 7919) % 18432), 1000 + static_cast<std::uint32_t>(i % 40),
                             (i * 6) & packed::time_mask});
  }
  std::vector<Single> out(n);
  for (auto _ : state) {
    packed::StreamDecoder d{ScannerGeometry::num_crystals};
    benchmark::DoNotOptimize(d.decode(words, out));
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * state.range(0));
  state.SetBytesProcessed(state.iterations() * state.range(0) * 8);
}
BENCHMARK(BM_DecodePacked)->Arg(1 << 16)->Arg(1 << 22)->Unit(benchmark::kMicrosecond);
