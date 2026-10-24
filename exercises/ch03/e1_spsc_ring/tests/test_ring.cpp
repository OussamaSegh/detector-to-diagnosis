// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <thread>
#include <vector>

#include "ring.hpp"

using ex::SinglesRing;
using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::Picoseconds;
using minidaq::Single;

namespace {
Single make(std::int64_t i) {
  return Single{Picoseconds{i}, CrystalId{static_cast<std::uint32_t>(i % 18'432)}, KeV{511.0F}};
}
// Stress loops give up after a deadline, so an unfinished ring fails the test
// instead of spinning forever.
class Deadline {
 public:
  explicit Deadline(std::chrono::seconds s) : end_{std::chrono::steady_clock::now() + s} {}
  [[nodiscard]] bool expired() {
    if (!expired_ && ++calls_ % 4096 == 0) {
      expired_ = std::chrono::steady_clock::now() > end_;
    }
    return expired_;
  }

 private:
  std::chrono::steady_clock::time_point end_;
  std::uint64_t calls_ = 0;
  bool expired_ = false;
};

// Declared after the producer thread, so it runs first on any exit from the
// test (including a failed ASSERT) and lets the producer finish before join.
struct ReleaseProducer {
  std::atomic<bool>& flag;
  ~ReleaseProducer() { flag.store(true); }
};
}  // namespace

TEST(SinglesRing, CapacityIsPowerOfTwo) {
  EXPECT_EQ(SinglesRing{1}.capacity(), 2U);
  EXPECT_EQ(SinglesRing{100}.capacity(), 128U);
  EXPECT_EQ(SinglesRing{256}.capacity(), 256U);
}

TEST(SinglesRing, FifoFullEmpty) {
  SinglesRing r{4};
  Single s{};
  EXPECT_FALSE(r.try_pop(s));
  for (int i = 0; i < 4; ++i) {
    ASSERT_TRUE(r.try_push(make(i)));
  }
  EXPECT_FALSE(r.try_push(make(4)));
  for (int i = 0; i < 4; ++i) {
    ASSERT_TRUE(r.try_pop(s));
    EXPECT_EQ(s, make(i));
  }
  EXPECT_FALSE(r.try_pop(s));
}

TEST(SinglesRing, ManyLaps) {
  SinglesRing r{8};
  std::int64_t in = 0;
  std::int64_t out = 0;
  Single s{};
  for (int lap = 0; lap < 500; ++lap) {
    while (r.try_push(make(in))) {
      ++in;
    }
    for (int k = 0; k < 3; ++k) {
      ASSERT_TRUE(r.try_pop(s));
      ASSERT_EQ(s, make(out++));
    }
  }
}

TEST(SinglesRing, BatchedPartial) {
  SinglesRing r{8};
  std::vector<Single> in;
  for (int i = 0; i < 6; ++i) {
    in.push_back(make(i));
  }
  EXPECT_EQ(r.try_push_n(in), 6U);
  EXPECT_EQ(r.try_push_n(in), 2U);
  std::array<Single, 16> out{};
  EXPECT_EQ(r.try_pop_n(out), 8U);
  EXPECT_EQ(out[5], make(5));
  EXPECT_EQ(out[7], make(1));
  EXPECT_EQ(r.try_pop_n(out), 0U);
}

TEST(SinglesRing, TwoThreadStress) {
  constexpr std::int64_t n = 2'000'000;
  SinglesRing r{1024};
  std::atomic<bool> give_up{false};
  std::jthread producer([&] {
    for (std::int64_t i = 0; i < n && !give_up.load(std::memory_order_relaxed);) {
      if (r.try_push(make(i))) {
        ++i;
      }
    }
  });
  ReleaseProducer release{give_up};
  Single s{};
  Deadline deadline{std::chrono::seconds{30}};
  for (std::int64_t i = 0; i < n;) {
    if (deadline.expired()) {
      FAIL() << "timed out after " << i << " singles";
    }
    if (r.try_pop(s)) {
      ASSERT_EQ(s, make(i)) << "lost, duplicated or torn single";
      ++i;
    }
  }
}

TEST(SinglesRing, TwoThreadBatchedStress) {
  constexpr std::int64_t n = 1'000'000;
  SinglesRing r{512};
  std::atomic<bool> give_up{false};
  std::jthread producer([&] {
    std::vector<Single> buf(100);
    for (std::int64_t i = 0; i < n && !give_up.load(std::memory_order_relaxed);) {
      for (std::size_t k = 0; k < buf.size(); ++k) {
        buf[k] = make(i + static_cast<std::int64_t>(k));
      }
      std::size_t off = 0;
      while (off < buf.size() && !give_up.load(std::memory_order_relaxed)) {
        off += r.try_push_n(std::span<const Single>(buf).subspan(off));
      }
      i += static_cast<std::int64_t>(buf.size());
    }
  });
  ReleaseProducer release{give_up};
  std::vector<Single> out(64);
  Deadline deadline{std::chrono::seconds{30}};
  for (std::int64_t i = 0; i < n;) {
    if (deadline.expired()) {
      FAIL() << "timed out after " << i << " singles";
    }
    const std::size_t got = r.try_pop_n(out);
    for (std::size_t k = 0; k < got; ++k) {
      ASSERT_EQ(out[k], make(i));
      ++i;
    }
  }
}
