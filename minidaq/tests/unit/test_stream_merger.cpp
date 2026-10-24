// SPDX-License-Identifier: MIT
// Merging per-board streams (Chapter 10): the merged stream is the time-ordered
// union of the inputs, nothing is released before every board has reported a
// later time, and a board that falls too far behind loses its late singles,
// counted.
#include <gtest/gtest.h>

#include <algorithm>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/processing/stream_merger.hpp"
#include "minidaq/sim/synthetic_source.hpp"
#include "minidaq/format/packed_single.hpp"

using namespace minidaq;

namespace {

// The merged stream is in time order. Equal times from one board keep that
// board's order; equal times from different boards come out by crystal.
bool by_time(const Single& a, const Single& b) { return a.time < b.time; }

Single at(std::int64_t t, std::uint32_t crystal = 0) { return Single{Picoseconds{t}, CrystalId{crystal}, KeV{511.0F}}; }

// A realistic stream, decoded, split into `n` boards by crystal.
std::vector<std::vector<Single>> boards_of(std::size_t n, std::size_t count, std::vector<Single>& all) {
  std::vector<std::uint64_t> words(count);
  sim::SyntheticSource gen{{.rate_hz = 20e6, .seed = 5}};
  gen.generate(words);
  all.resize(count);
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  all.resize(dec.decode(words, all));
  std::vector<std::vector<Single>> b(n);
  for (const Single& s : all) {
    b[s.crystal.value() % n].push_back(s);
  }
  std::stable_sort(all.begin(), all.end(), TimeOrder{});
  return b;
}

}  // namespace

TEST(StreamMerger, MergesInterleavedChunksIntoOneOrderedStream) {
  // REQ: SRS-MRG-001
  std::vector<Single> all;
  auto boards = boards_of(12, 100'000, all);
  StreamMerger m{{.boards = boards.size(), .max_skew = Picoseconds{0}}};
  std::vector<std::size_t> pos(boards.size(), 0);
  std::mt19937_64 rng{1};
  std::vector<Single> out;
  bool more = true;
  while (more) {
    more = false;
    for (std::size_t b = 0; b < boards.size(); ++b) {
      // Boards deliver chunks of random size: sometimes nothing, sometimes a lot.
      const std::size_t n = std::min<std::size_t>(boards[b].size() - pos[b], rng() % 400);
      m.push(b, std::span{boards[b]}.subspan(pos[b], n));
      pos[b] += n;
      more = more || pos[b] < boards[b].size();
    }
    m.drain(out);
    ASSERT_TRUE(std::is_sorted(out.begin(), out.end(), by_time));
  }
  m.flush(out);
  ASSERT_EQ(out.size(), all.size());
  for (std::size_t i = 0; i < all.size(); ++i) {
    ASSERT_EQ(out[i].time, all[i].time) << i;
  }
  EXPECT_EQ(m.stats().late, 0U);
  EXPECT_EQ(m.stats().singles_out, all.size());
  EXPECT_EQ(m.held(), 0U);
}

TEST(StreamMerger, WaitsForEveryBoard) {
  // REQ: SRS-MRG-002
  StreamMerger m{{.boards = 3, .max_skew = Picoseconds{0}}};
  std::vector<Single> out;
  const std::vector<Single> a{at(10), at(20), at(30)};
  m.push(0, a);
  m.push(1, std::vector<Single>{at(25)});
  m.drain(out);
  EXPECT_TRUE(out.empty()) << "board 2 has not reported";
  m.advance(2, Picoseconds{21});  // a time marker: nothing before 21 ps from board 2
  m.drain(out);
  ASSERT_EQ(out.size(), 2U) << "10 and 20 are earlier than min(30, 25, 21)";
  EXPECT_EQ(m.watermark(), Picoseconds{21});
  m.push(1, std::vector<Single>{at(25)});  // the same time again is allowed
  m.advance(2, Picoseconds{40});
  m.drain(out);
  EXPECT_EQ(out.size(), 2U) << "board 1 is at 25 and may still send another 25";
  m.push(0, std::vector<Single>{at(31)});
  m.push(1, std::vector<Single>{at(35)});
  m.drain(out);
  EXPECT_EQ(out.size(), 5U) << "30, 25, 25 released; watermark 31";
}

TEST(StreamMerger, ASlowBoardLosesOnlyItsLateSingles) {
  // REQ: SRS-MRG-003
  // Board 1 is 10 us behind board 0; max_skew is 5 us, so the watermark runs
  // ahead of board 1 and its singles arrive late.
  constexpr std::int64_t us = 1'000'000;
  StreamMerger m{{.boards = 2, .max_skew = Picoseconds{5 * us}}};
  std::vector<Single> out;
  for (std::int64_t t = 0; t < 100 * us; t += us) {
    m.push(0, std::vector<Single>{at(t)});
    if (t >= 10 * us) {
      m.push(1, std::vector<Single>{at(t - 10 * us + 1)});
    }
    m.drain(out);
  }
  m.flush(out);
  EXPECT_TRUE(std::is_sorted(out.begin(), out.end(), by_time));
  const auto& st = m.stats();
  EXPECT_EQ(st.singles_in, st.singles_out + st.late);
  EXPECT_GT(st.late, 80U) << "almost all of board 1 is late";
  EXPECT_GT(st.skew_releases, 0U);
  // With an unlimited wait, nothing is late (the merger holds 10 us of data).
  StreamMerger patient{{.boards = 2, .max_skew = Picoseconds{0}}};
  for (std::int64_t t = 0; t < 100 * us; t += us) {
    patient.push(0, std::vector<Single>{at(t)});
    if (t >= 10 * us) {
      patient.push(1, std::vector<Single>{at(t - 10 * us + 1)});
    }
    patient.drain(out);
  }
  EXPECT_EQ(patient.stats().late, 0U);
  EXPECT_GE(patient.held(), 10U);
}

TEST(StreamMerger, CountsABoardThatGoesBackInTime) {
  // REQ: SRS-MRG-004
  StreamMerger m{{.boards = 1}};
  std::vector<Single> out;
  m.push(0, std::vector<Single>{at(10), at(5), at(10), at(11)});
  m.advance(0, Picoseconds{20});
  m.push(0, std::vector<Single>{at(19)});
  m.flush(out);
  EXPECT_EQ(m.stats().out_of_order, 2U) << "5 after 10, and 19 after the promise of 20";
  EXPECT_EQ(out.size(), 3U);
  EXPECT_THROW((StreamMerger{{.boards = 0}}), std::invalid_argument);
}

TEST(StreamMerger, TiesComeOutInADeterministicOrder) {
  // REQ: SRS-MRG-005
  StreamMerger m{{.boards = 3}};
  std::vector<Single> out;
  m.push(2, std::vector<Single>{at(7, 1)});
  m.push(0, std::vector<Single>{at(7, 9)});
  m.push(1, std::vector<Single>{at(7, 1)});
  m.flush(out);
  ASSERT_EQ(out.size(), 3U);
  EXPECT_EQ(out[0].crystal, CrystalId{1});
  EXPECT_EQ(out[1].crystal, CrystalId{1});
  EXPECT_EQ(out[2].crystal, CrystalId{9}) << "time, then crystal, then board";
}
