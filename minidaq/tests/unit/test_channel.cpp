// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <thread>

#include "minidaq/pipeline/channel.hpp"

using minidaq::Batch;
using minidaq::Channel;

TEST(Channel, BatchesCirculateWithoutAllocation) {
  Channel<int> ch{2, 8};
  EXPECT_EQ(ch.num_batches(), 2U);
  Batch<int>* a = ch.acquire();
  Batch<int>* b = ch.acquire();
  ASSERT_NE(a, nullptr);
  ASSERT_NE(b, nullptr);
  EXPECT_EQ(ch.acquire(), nullptr) << "pool exhausted: this is where back-pressure starts";
  a->push_unchecked(1);
  ch.publish(a);
  Batch<int>* r = ch.receive();
  ASSERT_EQ(r, a);
  EXPECT_EQ(r->size, 1U);
  EXPECT_EQ(r->sequence, 0U);
  ch.release(r);
  Batch<int>* again = ch.acquire();
  EXPECT_EQ(again, a) << "the same storage comes back";
  EXPECT_EQ(again->size, 0U) << "acquire clears the batch";
  ch.release_unused(again);  // e.g. the source had no data after all
  EXPECT_EQ(ch.acquire(), again) << "an unused batch is handed out again first";
  ch.release_unused(again);
  ch.publish(b);
}

TEST(Channel, SequenceNumbersIncrease) {
  Channel<int> ch{4, 1};
  for (std::uint64_t i = 0; i < 10; ++i) {
    Batch<int>* b = ch.acquire();
    ASSERT_NE(b, nullptr);
    ch.publish(b);
    Batch<int>* r = ch.receive();
    ASSERT_NE(r, nullptr);
    EXPECT_EQ(r->sequence, i);
    ch.release(r);
  }
}

TEST(ChannelStress, CloseAfterLastPublishIsNeverMissed) {
  // REQ: SRS-PIPE-004
  // The consumer must see every batch published before close(), even if it
  // observes closed() between the producer's last publish and close().
  for (int trial = 0; trial < 200; ++trial) {
    Channel<std::uint64_t> ch{4, 16};
    constexpr std::uint64_t batches = 50;
    std::jthread producer([&] {
      for (std::uint64_t i = 0; i < batches;) {
        if (Batch<std::uint64_t>* b = ch.acquire()) {
          b->push_unchecked(i);
          ch.publish(b);
          ++i;
        }
      }
      ch.close();
    });
    std::uint64_t got = 0;
    for (;;) {
      Batch<std::uint64_t>* b = ch.receive();
      if (b == nullptr) {
        if (ch.closed() && (b = ch.receive()) == nullptr) {
          break;
        }
        if (b == nullptr) {
          continue;
        }
      }
      ASSERT_EQ(b->items[0], got);
      ++got;
      ch.release(b);
    }
    ASSERT_EQ(got, batches) << "trial " << trial;
  }
}
