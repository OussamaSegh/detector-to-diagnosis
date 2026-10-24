// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <cstdint>
#include <memory>
#include <random>
#include <thread>

#include "monitor.hpp"

TEST(EnergyMonitor, TwoWritersCountEverything) {
  ex::EnergyMonitor m;
  constexpr int per_thread = 500'000;
  auto writer = [&](unsigned seed) {
    std::mt19937 rng{seed};
    std::normal_distribution<float> e{511.0F, 30.0F};
    for (int i = 0; i < per_thread; ++i) {
      m.record(e(rng));
    }
  };
  {
    std::jthread a{writer, 1U};
    std::jthread b{writer, 2U};
  }
  std::uint64_t sum = 0;
  for (std::size_t i = 0; i < ex::EnergyMonitor::num_bins; ++i) {
    sum += m.bin(i);
  }
  EXPECT_EQ(m.total(), 2U * per_thread) << "lost updates on total";
  EXPECT_EQ(sum, 2U * per_thread) << "lost updates in the bins";
}

TEST(EnergyMonitor, WindowIsNeverSeenHalfWritten) {
  // On the heap on purpose: with Clang 18 at -O1 and above, TSan did not
  // instrument the reader's loads from a stack-allocated monitor and missed
  // this race (see Section 3.5). Shared objects in real code live on the heap.
  auto owner = std::make_unique<ex::EnergyMonitor>();
  ex::EnergyMonitor& m = *owner;
  ex::EnergyWindow w{};
  EXPECT_FALSE(m.current_window(w));
  // The control thread keeps publishing until the reader has seen enough
  // windows, so publication and reads are guaranteed to overlap in time
  // (TSan can only report accesses that actually happen concurrently).
  std::atomic<bool> reader_done{false};
  std::jthread control([&] {
    // Windows always satisfy high = low + 100, so a mixed read is detectable.
    for (int i = 0; !reader_done.load(); ++i) {
      const float low = 400.0F + static_cast<float>(i % 50);
      m.publish_window({low, low + 100.0F});
    }
  });
  for (int seen = 0; seen < 2'000;) {
    if (m.current_window(w)) {
      if (w.high_kev - w.low_kev != 100.0F) {
        reader_done.store(true);
        FAIL() << "torn window: " << w.low_kev << " to " << w.high_kev;
      }
      ++seen;
    }
  }
  reader_done.store(true);
}
