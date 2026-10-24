// SPDX-License-Identifier: MIT
// Memory-model litmus tests (Chapter 3). They demonstrate on real hardware
// what the C++ memory model allows, and check what it guarantees.
// MINIDAQ_LITMUS_TRIALS sets the number of trials (default 200,000).
#include <gtest/gtest.h>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>

#include "minidaq/core/cache.hpp"

namespace {

int trials() {
  if (const char* env = std::getenv("MINIDAQ_LITMUS_TRIALS")) {
    return std::stoi(env);
  }
  return 200'000;
}

struct alignas(minidaq::cache_line_size) Cell {
  std::atomic<int> v{0};
};

// [snippet:sb]
// Store buffering: thread A does x = 1; r1 = y. Thread B does y = 1; r2 = x.
// Can both threads read 0? Under seq_cst, no: there is a single total order
// of the four operations, and whichever store comes first is seen by the
// other thread's load. With release stores and acquire loads, yes: nothing
// orders a store before a *later load of a different variable*, and x86
// store buffers really do let the load overtake the store.
template <std::memory_order Store, std::memory_order Load>
std::uint64_t store_buffering(int n) {
  Cell x, y, go, done;
  int r2 = 0;  // written by B before done.store(release), read by A after done.load(acquire)
  std::uint64_t both_zero = 0;
  std::jthread b([&] {
    for (int i = 1; i <= n; ++i) {
      while (go.v.load(std::memory_order_acquire) != i) {
      }
      y.v.store(1, Store);
      r2 = x.v.load(Load);
      done.v.store(i, std::memory_order_release);
    }
  });
  for (int i = 1; i <= n; ++i) {  // thread A
    x.v.store(0, std::memory_order_relaxed);
    y.v.store(0, std::memory_order_relaxed);
    go.v.store(i, std::memory_order_release);  // start trial i
    x.v.store(1, Store);
    const int r1 = y.v.load(Load);
    while (done.v.load(std::memory_order_acquire) != i) {
    }
    both_zero += (r1 == 0 && r2 == 0) ? 1U : 0U;
  }
  return both_zero;
}
// [/snippet:sb]

}  // namespace

TEST(MemoryModel, StoreBufferingNeverBothZeroWithSeqCst) {
  // REQ: (teaching test, no requirement)
  const int n = trials();
  const auto seq = store_buffering<std::memory_order_seq_cst, std::memory_order_seq_cst>(n);
  const auto acq_rel = store_buffering<std::memory_order_release, std::memory_order_acquire>(n);
  std::printf("store buffering, %d trials: both-zero seq_cst=%llu acquire/release=%llu\n", n,
              static_cast<unsigned long long>(seq), static_cast<unsigned long long>(acq_rel));
  RecordProperty("acq_rel_both_zero", std::to_string(acq_rel));
  EXPECT_EQ(seq, 0U) << "forbidden by the C++ memory model";
  // acq_rel may be zero or not: the model allows it, the hardware decides.
}

// [snippet:mp]
// Message passing: the pattern every queue in this chapter relies on. If the
// consumer's acquire load sees the flag written by the producer's release
// store, everything the producer wrote before the store is visible.
TEST(MemoryModel, MessagePassingWithReleaseAcquire) {
  for (int round = 0; round < 2'000; ++round) {
    std::uint64_t payload = 0;  // plain, non-atomic data
    std::atomic<bool> ready{false};
    std::jthread producer([&] {
      payload = 0xC0FFEE + static_cast<std::uint64_t>(round);
      ready.store(true, std::memory_order_release);
    });
    while (!ready.load(std::memory_order_acquire)) {
    }
    ASSERT_EQ(payload, 0xC0FFEE + static_cast<std::uint64_t>(round));
  }
}
// [/snippet:mp]
