// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "drop_queue.hpp"

using ex::DropQueue;
using ex::Policy;
using ex::PushResult;

TEST(DropQueue, RejectKeepsContentsAndRefuses) {
  DropQueue<int> q{2, Policy::reject};
  EXPECT_EQ(q.push(1), PushResult::accepted);
  EXPECT_EQ(q.push(2), PushResult::accepted);
  EXPECT_EQ(q.push(3), PushResult::rejected);
  EXPECT_EQ(q.pop(), 1);
  EXPECT_EQ(q.pop(), 2);
  EXPECT_FALSE(q.pop().has_value());
  EXPECT_EQ(q.stats().rejected, 1U);
}

TEST(DropQueue, DropNewestDiscardsIncoming) {
  DropQueue<int> q{2, Policy::drop_newest};
  q.push(1);
  q.push(2);
  EXPECT_EQ(q.push(3), PushResult::dropped_newest);
  EXPECT_EQ(q.pop(), 1);
  EXPECT_EQ(q.pop(), 2);
  EXPECT_EQ(q.stats().dropped_newest, 1U);
}

TEST(DropQueue, DropOldestEvicts) {
  DropQueue<int> q{2, Policy::drop_oldest};
  q.push(1);
  q.push(2);
  EXPECT_EQ(q.push(3), PushResult::accepted_evicted_oldest);
  EXPECT_EQ(q.pop(), 2);
  EXPECT_EQ(q.pop(), 3);
  EXPECT_EQ(q.stats().dropped_oldest, 1U);
  EXPECT_EQ(q.stats().accepted, 3U);
}

TEST(DropQueue, AccountingInvariantUnderRandomTraffic) {
  for (Policy p : {Policy::reject, Policy::drop_newest, Policy::drop_oldest}) {
    DropQueue<int> q{16, p};
    std::mt19937 rng{42};
    std::uniform_int_distribution<int> op{0, 9};
    std::uint64_t offered = 0;
    for (int i = 0; i < 100'000; ++i) {
      if (op(rng) < 6) {  // offer more than we take: the queue fills up
        q.push(i);
        ++offered;
      } else {
        q.pop();
      }
      const auto& s = q.stats();
      ASSERT_EQ(s.accepted, s.popped + s.dropped_oldest + q.size());
      ASSERT_EQ(offered, s.accepted + s.rejected + s.dropped_newest);
    }
    EXPECT_GT(q.stats().rejected + q.stats().dropped_newest + q.stats().dropped_oldest, 0U);
  }
}

TEST(CountLost, GapsAndReordering) {
  const std::vector<std::uint64_t> clean{5, 6, 7, 8};
  EXPECT_EQ(ex::count_lost(clean, 5).lost, 0U);
  const std::vector<std::uint64_t> gaps{0, 1, 4, 5, 9};
  EXPECT_EQ(ex::count_lost(gaps, 0).lost, 5U);  // 2, 3, 6, 7, 8
  const std::vector<std::uint64_t> start_late{3, 4};
  EXPECT_EQ(ex::count_lost(start_late, 0).lost, 3U);
  const std::vector<std::uint64_t> dup{0, 1, 1, 2, 0};
  const auto r = ex::count_lost(dup, 0);
  EXPECT_EQ(r.lost, 0U);
  EXPECT_EQ(r.out_of_order, 2U);
}
