// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <cstdint>
#include <thread>
#include <vector>

#include "minidaq/pipeline/mpmc_queue.hpp"

using minidaq::MpmcQueue;

TEST(MpmcQueue, SingleThreadFifo) {
  MpmcQueue<int> q{4};
  EXPECT_EQ(q.capacity(), 4U);
  for (int i = 0; i < 4; ++i) {
    EXPECT_TRUE(q.try_push(i));
  }
  EXPECT_FALSE(q.try_push(4));
  for (int i = 0; i < 4; ++i) {
    EXPECT_EQ(q.try_pop(), i);
  }
  EXPECT_FALSE(q.try_pop().has_value());
}

TEST(MpmcQueueStress, FourProducersTwoConsumersExactlyOnce) {
  // REQ: SRS-PIPE-003
  constexpr int producers = 4;
  constexpr int consumers = 2;
  constexpr std::uint32_t per_producer = 200'000;
  MpmcQueue<std::uint64_t> q{1024};
  std::vector<std::atomic<std::uint8_t>> seen(producers * std::size_t{per_producer});
  std::atomic<std::uint64_t> consumed{0};
  {
    std::vector<std::jthread> threads;
    for (int p = 0; p < producers; ++p) {
      threads.emplace_back([&, p] {
        for (std::uint32_t i = 0; i < per_producer;) {
          // Value encodes producer and index, so every item is unique.
          if (q.try_push(static_cast<std::uint64_t>(p) * per_producer + i)) {
            ++i;
          }
        }
      });
    }
    for (int c = 0; c < consumers; ++c) {
      threads.emplace_back([&] {
        while (consumed.load(std::memory_order_relaxed) < producers * std::uint64_t{per_producer}) {
          if (auto v = q.try_pop()) {
            seen[*v].fetch_add(1, std::memory_order_relaxed);
            consumed.fetch_add(1, std::memory_order_relaxed);
          }
        }
      });
    }
  }
  for (std::size_t i = 0; i < seen.size(); ++i) {
    ASSERT_EQ(seen[i].load(), 1U) << "item " << i << " not delivered exactly once";
  }
}

TEST(MpmcQueueStress, PerProducerOrderIsPreserved) {
  // With one consumer, items from any single producer arrive in order.
  constexpr int producers = 3;
  constexpr std::uint32_t per_producer = 100'000;
  MpmcQueue<std::uint64_t> q{256};
  std::vector<std::jthread> threads;
  for (int p = 0; p < producers; ++p) {
    threads.emplace_back([&, p] {
      for (std::uint32_t i = 0; i < per_producer;) {
        if (q.try_push((static_cast<std::uint64_t>(p) << 32) | i)) {
          ++i;
        }
      }
    });
  }
  std::vector<std::int64_t> last(producers, -1);
  for (std::uint64_t got = 0; got < producers * std::uint64_t{per_producer};) {
    if (auto v = q.try_pop()) {
      const auto p = static_cast<std::size_t>(*v >> 32);
      const auto i = static_cast<std::int64_t>(*v & 0xFFFF'FFFFU);
      ASSERT_GT(i, last[p]);
      last[p] = i;
      ++got;
    }
  }
}
