// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 21.3. The concurrent test is meant for the tsan preset too.
#include <gtest/gtest.h>

#include <atomic>
#include <thread>
#include <vector>

#include "tiny_recorder.hpp"

using ex21::Event;
using ex21::TinyRecorder;

namespace {
std::vector<Event> take(const TinyRecorder& r, std::size_t n = TinyRecorder::kEvents) {
  std::vector<Event> out(n);
  out.resize(r.snapshot(out));
  return out;
}
}  // namespace

TEST(TinyRecorder, KeepsEventsInOrder) {
  TinyRecorder r;
  EXPECT_TRUE(take(r).empty());
  for (std::uint64_t i = 1; i <= 10; ++i) {
    r.record(i, 100 + i);
  }
  const auto e = take(r);
  ASSERT_EQ(e.size(), 10U);
  for (std::uint64_t i = 0; i < 10; ++i) {
    EXPECT_EQ(e[i].seq, i + 1);
    EXPECT_EQ(e[i].a, i + 1);
    EXPECT_EQ(e[i].b, 101 + i);
  }
}

TEST(TinyRecorder, KeepsTheLastEventsWhenItWraps) {
  TinyRecorder r;
  for (std::uint64_t i = 1; i <= 1000; ++i) {
    r.record(i, 0);
  }
  const auto e = take(r);
  ASSERT_EQ(e.size(), TinyRecorder::kEvents);
  EXPECT_EQ(e.front().seq, 1000 - TinyRecorder::kEvents + 1);
  EXPECT_EQ(e.back().seq, 1000U);
  EXPECT_EQ(e.back().a, 1000U);
}

TEST(TinyRecorder, ASmallSnapshotKeepsTheNewest) {
  TinyRecorder r;
  for (std::uint64_t i = 1; i <= 20; ++i) {
    r.record(i, 0);
  }
  const auto e = take(r, 3);
  ASSERT_EQ(e.size(), 3U);
  EXPECT_EQ(e[0].a, 18U);
  EXPECT_EQ(e[2].a, 20U);
}

TEST(TinyRecorder, ASnapshotNeverHoldsHalfAnEvent) {
  TinyRecorder r;
  std::atomic<bool> stop{false};
  std::thread writer{[&] {
    for (std::uint64_t i = 1; !stop.load(std::memory_order_relaxed); ++i) {
      r.record(i, ~i);  // b is always the complement of a, and a is the event's number
    }
  }};
  std::size_t seen = 0;
  for (int k = 0; k < 20000; ++k) {
    const auto e = take(r);
    for (std::size_t i = 0; i < e.size(); ++i) {
      ASSERT_EQ(e[i].b, ~e[i].a) << "half of an event";
      ASSERT_EQ(e[i].a, e[i].seq) << "an event in another event's slot";
      if (i > 0) {
        ASSERT_EQ(e[i].seq, e[i - 1].seq + 1) << "a gap in the middle of a snapshot";
      }
    }
    seen += e.size();
  }
  stop.store(true);
  writer.join();
  EXPECT_GT(seen, 0U);
}
