// SPDX-License-Identifier: MIT
// Exercise 3.1: throughput between two pinned threads (CPUs 0 and 1).
#include <benchmark/benchmark.h>
#include <pthread.h>
#include <sched.h>

#include <cstdint>
#include <thread>
#include <vector>

#include "ring.hpp"

namespace {

constexpr std::int64_t kItems = 1 << 22;

void pin_to(int cpu) {
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(static_cast<unsigned>(cpu), &set);
  (void)pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
}

void BM_SinglesRing(benchmark::State& state) {
  pin_to(1);
  ex::SinglesRing r{4096};
  std::int64_t sum = 0;
  for (auto _ : state) {
    std::jthread producer([&r] {
      pin_to(0);
      minidaq::Single s{};
      for (std::int64_t i = 0; i < kItems;) {
        s.time = minidaq::Picoseconds{i};
        if (r.try_push(s)) {
          ++i;
        }
      }
    });
    minidaq::Single s{};
    for (std::int64_t i = 0; i < kItems;) {
      if (r.try_pop(s)) {
        sum += s.time.count();
        ++i;
      }
    }
  }
  benchmark::DoNotOptimize(sum);
  state.SetItemsProcessed(state.iterations() * kItems);
}

void BM_SinglesRingBatched(benchmark::State& state) {
  pin_to(1);
  const auto batch = static_cast<std::size_t>(state.range(0));
  ex::SinglesRing r{4096};
  std::vector<minidaq::Single> out(batch);
  std::int64_t sum = 0;
  for (auto _ : state) {
    std::jthread producer([&r, batch] {
      pin_to(0);
      std::vector<minidaq::Single> buf(batch);
      for (std::int64_t i = 0; i < kItems;) {
        for (std::size_t k = 0; k < batch; ++k) {
          buf[k].time = minidaq::Picoseconds{i + static_cast<std::int64_t>(k)};
        }
        std::size_t off = 0;
        while (off < batch) {
          off += r.try_push_n(std::span<const minidaq::Single>(buf).subspan(off));
        }
        i += static_cast<std::int64_t>(batch);
      }
    });
    for (std::int64_t i = 0; i < kItems;) {
      const std::size_t n = r.try_pop_n(out);
      for (std::size_t k = 0; k < n; ++k) {
        sum += out[k].time.count();
      }
      i += static_cast<std::int64_t>(n);
    }
  }
  benchmark::DoNotOptimize(sum);
  state.SetItemsProcessed(state.iterations() * kItems);
}

}  // namespace

BENCHMARK(BM_SinglesRing)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_SinglesRingBatched)->Arg(64)->Arg(256)->UseRealTime()->Unit(benchmark::kMillisecond);
