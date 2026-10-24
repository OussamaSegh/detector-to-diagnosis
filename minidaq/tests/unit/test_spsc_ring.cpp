// SPDX-License-Identifier: MIT
// SPSC ring: single-threaded semantics, then a two-thread stress test that
// TSan checks for data races (run the tsan preset).
#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <memory>
#include <thread>
#include <vector>

#include "minidaq/pipeline/spsc_ring.hpp"

using minidaq::SpscRing;

TEST(SpscRing, CapacityRoundsUpToPowerOfTwo) {
  EXPECT_EQ(SpscRing<int>{0}.capacity(), 2U);
  EXPECT_EQ(SpscRing<int>{5}.capacity(), 8U);
  EXPECT_EQ(SpscRing<int>{1024}.capacity(), 1024U);
}

TEST(SpscRing, FifoOrderAndFullEmpty) {
  // REQ: SRS-PIPE-001
  SpscRing<int> r{4};
  EXPECT_FALSE(r.try_pop().has_value());
  for (int i = 0; i < 4; ++i) {
    EXPECT_TRUE(r.try_push(i));
  }
  EXPECT_FALSE(r.try_push(99)) << "a full ring must refuse";
  EXPECT_EQ(r.size_approx(), 4U);
  for (int i = 0; i < 4; ++i) {
    EXPECT_EQ(r.try_pop(), i);
  }
  EXPECT_FALSE(r.try_pop().has_value());
}

TEST(SpscRing, WrapsAroundManyTimes) {
  SpscRing<std::uint64_t> r{8};
  std::uint64_t next_in = 0;
  std::uint64_t next_out = 0;
  for (int round = 0; round < 1000; ++round) {
    while (r.try_push(std::uint64_t{next_in})) {
      ++next_in;
    }
    for (int k = 0; k < 5; ++k) {
      auto v = r.try_pop();
      ASSERT_TRUE(v.has_value());
      ASSERT_EQ(*v, next_out++);
    }
  }
}

TEST(SpscRing, MoveOnlyElements) {
  SpscRing<std::unique_ptr<int>> r{2};
  EXPECT_TRUE(r.try_push(std::make_unique<int>(7)));
  auto v = r.try_pop();
  ASSERT_TRUE(v && *v);
  EXPECT_EQ(**v, 7);
}

TEST(SpscRing, BatchPushPopPartial) {
  SpscRing<int> r{8};
  std::array<int, 6> in{1, 2, 3, 4, 5, 6};
  EXPECT_EQ(r.push_batch(in), 6U);
  EXPECT_EQ(r.push_batch(in), 2U) << "only two slots were free";
  std::array<int, 16> out{};
  EXPECT_EQ(r.pop_batch(out), 8U);
  EXPECT_EQ(out[0], 1);
  EXPECT_EQ(out[5], 6);
  EXPECT_EQ(out[6], 1);
  EXPECT_EQ(out[7], 2);
  EXPECT_EQ(r.pop_batch(out), 0U);
}

TEST(SpscRingStress, TwoThreadsPreserveEverySequenceNumber) {
  // REQ: SRS-PIPE-002
  constexpr std::uint64_t n = 2'000'000;
  SpscRing<std::uint64_t> r{1024};
  std::jthread producer([&] {
    for (std::uint64_t i = 0; i < n;) {
      if (r.try_push(std::uint64_t{i})) {
        ++i;
      }
    }
  });
  std::uint64_t expected = 0;
  while (expected < n) {
    if (auto v = r.try_pop()) {
      ASSERT_EQ(*v, expected) << "lost, duplicated or reordered element";
      ++expected;
    }
  }
}

TEST(SpscRingStress, BatchedTransferOfStructs) {
  // Payload larger than a word, so a torn read would show as a mismatch.
  struct Item {
    std::uint64_t a;
    std::uint64_t b;
  };
  constexpr std::uint64_t n = 1'000'000;
  SpscRing<Item> r{256};
  std::jthread producer([&] {
    std::vector<Item> buf(37);
    std::uint64_t i = 0;
    while (i < n) {
      std::size_t k = 0;
      for (; k < buf.size() && i + k < n; ++k) {
        buf[k] = Item{i + k, ~(i + k)};
      }
      std::size_t off = 0;
      while (off < k) {
        off += r.push_batch(std::span(buf).subspan(off, k - off));
      }
      i += k;
    }
  });
  std::vector<Item> out(64);
  std::uint64_t expected = 0;
  while (expected < n) {
    const std::size_t got = r.pop_batch(out);
    for (std::size_t k = 0; k < got; ++k) {
      ASSERT_EQ(out[k].a, expected);
      ASSERT_EQ(out[k].b, ~expected);
      ++expected;
    }
  }
}
