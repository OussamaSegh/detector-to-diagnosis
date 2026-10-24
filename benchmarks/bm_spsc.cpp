// SPDX-License-Identifier: MIT
// Queue throughput between two threads (Chapter 3). Each iteration moves
// kItems 64-bit values from a producer thread to the consumer (the benchmark
// thread). Variants isolate one design choice each:
//   Mutex     std::mutex + std::deque, the obvious first version
//   NaiveRing lock-free ring, but seq_cst atomics and no cached indices
//   AcqRelRing the same with acquire/release (isolates the fence cost)
//   SpscRing  minidaq::SpscRing (acquire/release, cached indices)
//   Batched   minidaq::SpscRing with push_batch/pop_batch of 256
//   Mpmc      minidaq::MpmcQueue used with one producer and one consumer
// Threads are pinned to CPUs 0 and 1 when possible (pass --benchmark_... as usual);
// set MINIDAQ_BENCH_CPUS="2,3" to choose other CPUs.
#include <benchmark/benchmark.h>
#include <pthread.h>
#include <sched.h>

#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "minidaq/core/cache.hpp"
#include "minidaq/pipeline/mpmc_queue.hpp"
#include "minidaq/pipeline/spsc_ring.hpp"

namespace {

constexpr std::uint64_t kItems = 1U << 22;  // about 4 M items per iteration
constexpr std::size_t kCapacity = 4096;

std::pair<int, int> bench_cpus() {
  if (const char* env = std::getenv("MINIDAQ_BENCH_CPUS")) {
    const std::string s{env};
    const auto comma = s.find(',');
    if (comma != std::string::npos) {
      return {std::stoi(s.substr(0, comma)), std::stoi(s.substr(comma + 1))};
    }
  }
  return {0, 1};
}

void pin_to(int cpu) {
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(static_cast<unsigned>(cpu), &set);
  (void)pthread_setaffinity_np(pthread_self(), sizeof(set), &set);  // best effort
}

class MutexQueue {
 public:
  bool try_push(std::uint64_t v) {
    std::lock_guard lock{m_};
    if (q_.size() == kCapacity) {
      return false;
    }
    q_.push_back(v);
    return true;
  }
  std::optional<std::uint64_t> try_pop() {
    std::lock_guard lock{m_};
    if (q_.empty()) {
      return std::nullopt;
    }
    const std::uint64_t v = q_.front();
    q_.pop_front();
    return v;
  }

 private:
  std::mutex m_;
  std::deque<std::uint64_t> q_;
};

// [snippet:naive]
// Correct, but every operation reads the other side's index (a cache line
// the other core keeps writing). With Order = seq_cst every store is also a
// full fence on x86 (an XCHG); with acquire/release it is a plain MOV.
template <std::memory_order Load, std::memory_order Store>
class UncachedRing {
 public:
  bool try_push(std::uint64_t v) {
    const std::size_t t = tail_.load(std::memory_order_relaxed);
    if (t - head_.load(Load) == kCapacity) {
      return false;
    }
    slots_[t % kCapacity] = v;
    tail_.store(t + 1, Store);
    return true;
  }
  std::optional<std::uint64_t> try_pop() {
    const std::size_t h = head_.load(std::memory_order_relaxed);
    if (h == tail_.load(Load)) {
      return std::nullopt;
    }
    const std::uint64_t v = slots_[h % kCapacity];
    head_.store(h + 1, Store);
    return v;
  }

 private:
  std::unique_ptr<std::uint64_t[]> slots_ = std::make_unique<std::uint64_t[]>(kCapacity);
  alignas(minidaq::cache_line_size) std::atomic<std::size_t> head_{0};
  alignas(minidaq::cache_line_size) std::atomic<std::size_t> tail_{0};
};
using NaiveRing = UncachedRing<std::memory_order_seq_cst, std::memory_order_seq_cst>;
using AcqRelRing = UncachedRing<std::memory_order_acquire, std::memory_order_release>;
// [/snippet:naive]

template <typename Q>
void run_single(benchmark::State& state, Q& q) {
  const auto [pcpu, ccpu] = bench_cpus();
  pin_to(ccpu);
  std::uint64_t checksum = 0;
  for (auto _ : state) {
    std::jthread producer([&q, producer_cpu = pcpu] {
      pin_to(producer_cpu);
      for (std::uint64_t i = 0; i < kItems;) {
        if (q.try_push(std::uint64_t{i})) {
          ++i;
        }
      }
    });
    for (std::uint64_t got = 0; got < kItems;) {
      if (auto v = q.try_pop()) {
        checksum += *v;
        ++got;
      }
    }
  }
  benchmark::DoNotOptimize(checksum);
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(kItems));
}

void BM_Mutex(benchmark::State& state) {
  MutexQueue q;
  run_single(state, q);
}
void BM_NaiveRing(benchmark::State& state) {
  NaiveRing q;
  run_single(state, q);
}
void BM_AcqRelRing(benchmark::State& state) {
  AcqRelRing q;
  run_single(state, q);
}
void BM_SpscRing(benchmark::State& state) {
  minidaq::SpscRing<std::uint64_t> q{kCapacity};
  run_single(state, q);
}
void BM_Mpmc(benchmark::State& state) {
  minidaq::MpmcQueue<std::uint64_t> q{kCapacity};
  run_single(state, q);
}

void BM_SpscRingBatched(benchmark::State& state) {
  const auto batch = static_cast<std::size_t>(state.range(0));
  const auto [pcpu, ccpu] = bench_cpus();
  pin_to(ccpu);
  minidaq::SpscRing<std::uint64_t> q{kCapacity};
  std::uint64_t checksum = 0;
  std::vector<std::uint64_t> out(batch);
  for (auto _ : state) {
    std::jthread producer([&q, batch, producer_cpu = pcpu] {
      pin_to(producer_cpu);
      std::vector<std::uint64_t> buf(batch);
      for (std::uint64_t i = 0; i < kItems;) {
        for (std::size_t k = 0; k < batch; ++k) {
          buf[k] = i + k;
        }
        std::size_t off = 0;
        while (off < batch) {
          off += q.push_batch(std::span(buf).subspan(off));
        }
        i += batch;
      }
    });
    for (std::uint64_t got = 0; got < kItems;) {
      const std::size_t n = q.pop_batch(out);
      for (std::size_t k = 0; k < n; ++k) {
        checksum += out[k];
      }
      got += n;
    }
  }
  benchmark::DoNotOptimize(checksum);
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(kItems));
}

}  // namespace

BENCHMARK(BM_Mutex)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_NaiveRing)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_AcqRelRing)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_SpscRing)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_Mpmc)->UseRealTime()->Unit(benchmark::kMillisecond);
BENCHMARK(BM_SpscRingBatched)->Arg(16)->Arg(256)->UseRealTime()->Unit(benchmark::kMillisecond);
