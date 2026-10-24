// SPDX-License-Identifier: MIT
// Memory latency by working-set size (Chapter 2): a dependent pointer chase
// through a random cyclic permutation, so every load waits for the previous one
// and hardware prefetchers cannot guess the next address.
#include <benchmark/benchmark.h>

#include <algorithm>
#include <cstddef>
#include <numeric>
#include <random>
#include <vector>

namespace {

// [snippet:chase]
struct alignas(64) Node {  // one node per cache line
  Node* next;
};

std::vector<Node> make_cycle(std::size_t bytes) {
  const std::size_t n = std::max<std::size_t>(bytes / sizeof(Node), 2);
  std::vector<Node> nodes(n);
  std::vector<std::size_t> order(n);
  std::iota(order.begin(), order.end(), std::size_t{0});
  std::shuffle(order.begin() + 1, order.end(), std::mt19937_64{12345});
  for (std::size_t i = 0; i < n; ++i) {
    nodes[order[i]].next = &nodes[order[(i + 1) % n]];
  }
  return nodes;
}

void BM_PointerChase(benchmark::State& state) {
  auto nodes = make_cycle(static_cast<std::size_t>(state.range(0)));
  Node* p = &nodes[0];
  constexpr int kSteps = 1 << 20;
  for (auto _ : state) {
    for (int i = 0; i < kSteps; ++i) {
      p = p->next;  // each load depends on the previous one
    }
    benchmark::DoNotOptimize(p);
  }
  // Report nanoseconds per load.
  state.counters["ns_per_load"] = benchmark::Counter(
      static_cast<double>(state.iterations()) * kSteps,
      benchmark::Counter::kIsRate | benchmark::Counter::kInvert);
}
// [/snippet:chase]

}  // namespace

BENCHMARK(BM_PointerChase)
    ->Arg(16 << 10)    // 16 KiB: L1
    ->Arg(512 << 10)   // 512 KiB: L2
    ->Arg(8 << 20)     // 8 MiB: L3
    ->Arg(64 << 20)    // 64 MiB: L3 on big server parts, DRAM elsewhere
    ->Arg(1 << 30)     // 1 GiB: DRAM (and TLB misses with 4 KiB pages)
    ->Unit(benchmark::kMillisecond);
