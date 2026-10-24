// SPDX-License-Identifier: MIT
// Heap allocation in an event loop vs a monotonic arena (Chapter 2).
#include <benchmark/benchmark.h>

#include <array>
#include <cstddef>
#include <memory_resource>
#include <random>
#include <vector>

#include "minidaq/core/single.hpp"

using namespace minidaq;

namespace {

constexpr std::size_t kBatch = 4096;

std::vector<Single> make_input() {
  std::mt19937 rng{3};
  std::normal_distribution<float> e{450.0F, 120.0F};
  std::vector<Single> v(kBatch * 64);
  for (std::size_t i = 0; i < v.size(); ++i) {
    v[i] = Single{Picoseconds{static_cast<std::int64_t>(i) * 40}, CrystalId{static_cast<std::uint32_t>(i % 18432)},
                  KeV{e(rng)}};
  }
  return v;
}

// [snippet:heap]
void BM_FilterBatches_Heap(benchmark::State& state) {
  const auto input = make_input();
  for (auto _ : state) {
    std::size_t kept = 0;
    for (std::size_t b = 0; b < input.size(); b += kBatch) {
      std::vector<Single> window;  // allocates and grows on every batch
      for (std::size_t i = b; i < b + kBatch; ++i) {
        if (input[i].energy.count() > 435.0F && input[i].energy.count() < 587.0F) {
          window.push_back(input[i]);
        }
      }
      kept += window.size();
    }
    benchmark::DoNotOptimize(kept);
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(input.size()));
}
// [/snippet:heap]

// [snippet:pmr]
void BM_FilterBatches_Monotonic(benchmark::State& state) {
  const auto input = make_input();
  // One arena, allocated once, big enough for a full batch plus vector growth.
  std::vector<std::byte> arena(4 * kBatch * sizeof(Single));
  for (auto _ : state) {
    std::size_t kept = 0;
    for (std::size_t b = 0; b < input.size(); b += kBatch) {
      // Bump-pointer allocation; null upstream makes overflow a hard error.
      std::pmr::monotonic_buffer_resource mr{arena.data(), arena.size(), std::pmr::null_memory_resource()};
      std::pmr::vector<Single> window{&mr};
      window.reserve(kBatch);
      for (std::size_t i = b; i < b + kBatch; ++i) {
        if (input[i].energy.count() > 435.0F && input[i].energy.count() < 587.0F) {
          window.push_back(input[i]);
        }
      }
      kept += window.size();
    }  // mr and window die here: "freeing" is resetting one pointer
    benchmark::DoNotOptimize(kept);
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(input.size()));
}
// [/snippet:pmr]

// The simplest fix of all: hoist the buffer out of the loop and clear() it.
void BM_FilterBatches_Reused(benchmark::State& state) {
  const auto input = make_input();
  std::vector<Single> window;
  window.reserve(kBatch);
  for (auto _ : state) {
    std::size_t kept = 0;
    for (std::size_t b = 0; b < input.size(); b += kBatch) {
      window.clear();  // keeps capacity: no allocation after the first batch
      for (std::size_t i = b; i < b + kBatch; ++i) {
        if (input[i].energy.count() > 435.0F && input[i].energy.count() < 587.0F) {
          window.push_back(input[i]);
        }
      }
      kept += window.size();
    }
    benchmark::DoNotOptimize(kept);
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(input.size()));
}

}  // namespace

BENCHMARK(BM_FilterBatches_Heap)->Unit(benchmark::kMicrosecond);
BENCHMARK(BM_FilterBatches_Monotonic)->Unit(benchmark::kMicrosecond);
BENCHMARK(BM_FilterBatches_Reused)->Unit(benchmark::kMicrosecond);
