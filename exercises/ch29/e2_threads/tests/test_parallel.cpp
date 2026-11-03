// SPDX-License-Identifier: MIT
// Acceptance tests of Exercise 29.2.
#include <gtest/gtest.h>

#include <atomic>
#include <cmath>
#include <random>
#include <stdexcept>
#include <vector>

#include "parallel.hpp"

namespace {

TEST(ParallelFor, CoversEveryIndexOnce) {
  for (const std::size_t count : {0U, 1U, 7U, 100U, 1001U, 43584U}) {
    for (unsigned threads = 0; threads <= 9; ++threads) {
      std::vector<std::atomic<int>> seen(count);
      std::atomic<int> calls{0};
      ex::parallel_for(count, threads, [&](std::size_t first, std::size_t last, unsigned) {
        ++calls;
        for (std::size_t i = first; i < last; ++i) ++seen[i];
      });
      for (std::size_t i = 0; i < count; ++i) {
        ASSERT_EQ(seen[i].load(), 1) << "index " << i << " of " << count << ", " << threads
                                     << " threads";
      }
      EXPECT_GE(calls.load(), 1);
      EXPECT_LE(calls.load(), static_cast<int>(std::max<std::size_t>(1, std::min<std::size_t>(
                                                   std::max(threads, 1U), count))));
    }
  }
}

struct Data {
  std::vector<std::size_t> index;
  std::vector<double> value;
  static constexpr std::size_t size = 500;
  Data() {
    // Many items per output, as many lines cross each pixel.
    std::mt19937_64 rng(29);
    std::uniform_int_distribution<std::size_t> where(0, size - 1);
    std::uniform_real_distribution<double> what(0.0, 1.0);
    for (int i = 0; i < 200'000; ++i) {
      index.push_back(where(rng));
      value.push_back(what(rng));
    }
  }
};

TEST(ScatterAdd, EveryThreadCountGivesTheSerialSum) {
  const Data d;
  const auto serial = ex::scatter_add(d.index, d.value, Data::size, 1);
  double total = 0.0;
  for (const double v : d.value) total += v;
  double got = 0.0;
  for (const double v : serial) got += v;
  EXPECT_NEAR(got, total, 1e-9 * total);
  for (unsigned threads = 2; threads <= 8; ++threads) {
    const auto parallel = ex::scatter_add(d.index, d.value, Data::size, threads);
    ASSERT_EQ(parallel.size(), serial.size());
    for (std::size_t i = 0; i < serial.size(); ++i) {
      ASSERT_NEAR(parallel[i], serial[i], 1e-12 * serial[i]) << "output " << i << ", " << threads
                                                            << " threads";
    }
  }
}

TEST(ScatterAdd, TheSameThreadCountGivesTheSameBits) {
  const Data d;
  const auto first = ex::scatter_add(d.index, d.value, Data::size, 4);
  for (int run = 0; run < 10; ++run) {
    ASSERT_EQ(ex::scatter_add(d.index, d.value, Data::size, 4), first) << "run " << run;
  }
}

TEST(ScatterAdd, RefusesAnIndexOutsideTheOutput) {
  const std::vector<std::size_t> index{0, 3, 5};
  const std::vector<double> value{1.0, 1.0, 1.0};
  EXPECT_THROW(ex::scatter_add(index, value, 5, 2), std::out_of_range);
  EXPECT_EQ(ex::scatter_add({}, {}, 3, 4), std::vector<double>(3, 0.0));
}

}  // namespace
