// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/processing/stream_merger.hpp"
#include "slice_merge.hpp"

using namespace minidaq;

namespace {

// `n` boards, each a TimeOrder-sorted stream; times on a coarse grid so that
// ties across boards and singles exactly on slice edges are common.
std::vector<std::vector<Single>> boards(std::size_t n, std::size_t per_board, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::vector<std::vector<Single>> b(n);
  for (std::size_t i = 0; i < n; ++i) {
    std::int64_t t = static_cast<std::int64_t>(rng() % 1000) * 1'000;
    for (std::size_t k = 0; k < per_board; ++k) {
      t += static_cast<std::int64_t>(rng() % 4) * 1'000;  // steps of 0 to 3 ns
      b[i].push_back(Single{Picoseconds{t}, CrystalId{static_cast<std::uint32_t>(rng() % 4)}, KeV{511.0F}});
    }
    std::stable_sort(b[i].begin(), b[i].end(), TimeOrder{});
  }
  return b;
}

std::vector<Single> heap_merge(const std::vector<std::vector<Single>>& b) {
  StreamMerger m{{.boards = b.size(), .max_skew = Picoseconds{0}}};
  for (std::size_t i = 0; i < b.size(); ++i) {
    m.push(i, b[i]);
  }
  std::vector<Single> out;
  m.flush(out);
  return out;
}

}  // namespace

TEST(SliceMerge, EqualsTheHeapMerger) {
  for (std::size_t n : {1U, 4U, 24U, 72U}) {
    const auto b = boards(n, 2'000, n);
    const auto want = heap_merge(b);
    for (std::int64_t slice : {1'000, 7'000, 100'000, 10'000'000}) {
      EXPECT_EQ(ex105::merge_by_slices(b, Picoseconds{slice}), want) << n << " boards, slice " << slice << " ps";
    }
  }
}

TEST(SliceMerge, EdgesAndEmptyBoards) {
  const auto s = [](std::int64_t t, std::uint32_t c) { return Single{Picoseconds{t}, CrystalId{c}, KeV{511.0F}}; };
  // Singles exactly on slice edges (slices of 10 ps from t = 0), the last one alone in its slice.
  const std::vector<std::vector<Single>> b{{s(0, 1), s(10, 1), s(20, 1)}, {}, {s(10, 0), s(35, 2)}};
  const auto got = ex105::merge_by_slices(b, Picoseconds{10});
  ASSERT_EQ(got.size(), 5U);
  EXPECT_EQ(got, heap_merge(b));
  EXPECT_EQ(got.back().time, Picoseconds{35}) << "the last, partial slice is not forgotten";
  EXPECT_TRUE(ex105::merge_by_slices(std::vector<std::vector<Single>>(3), Picoseconds{10}).empty());
}
