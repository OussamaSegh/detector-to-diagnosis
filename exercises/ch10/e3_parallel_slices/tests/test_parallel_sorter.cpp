// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "parallel_sorter.hpp"

using namespace minidaq;

namespace {

std::vector<Coincidence> serial(std::span<const Single> in, const SorterConfig& c) {
  CoincidenceSorter s{c};
  std::vector<Coincidence> out;
  s.push(in, out);
  s.flush(out);
  return out;
}

std::vector<Single> simulated(double activity, double seconds, std::uint64_t seed) {
  sim::SimulatorConfig c;
  c.activity_bq = activity;
  c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  c.seed = seed;
  sim::DetectorSimulator d{c};
  std::vector<Single> v;
  for (const auto& t : d.generate_until(Picoseconds{static_cast<std::int64_t>(seconds * 1e12)})) {
    v.push_back(t.single);
  }
  return v;
}

}  // namespace

TEST(ParallelSorter, SameResultAsOneSorterOnSimulatedData) {
  const auto in = simulated(30e6, 0.01, 4);
  for (auto policy : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods}) {
    SorterConfig c;
    c.multiples = policy;
    const auto want = serial(in, c);
    for (unsigned t : {1U, 2U, 3U, 4U, 7U}) {
      EXPECT_EQ(ex103::sort_parallel(in, c, t), want) << t << " threads, " << to_string(policy);
    }
  }
}

TEST(ParallelSorter, DenseStreamsWithFewGaps) {
  // Singles every 0 to 5 ns: gaps wider than the 4 ns window are rare, and
  // nominal cuts nearly always fall inside a window. Random energies put
  // rejected singles between accepted ones.
  std::mt19937_64 rng{9};
  std::vector<Single> in;
  std::int64_t t = 0;
  for (int i = 0; i < 200'000; ++i) {
    t += static_cast<std::int64_t>(rng() % 5'001);
    in.push_back(Single{Picoseconds{t}, CrystalId{static_cast<std::uint32_t>(rng() % ScannerGeometry::num_crystals)},
                        KeV{static_cast<float>(400 + rng() % 200)}});
  }
  SorterConfig c;
  c.multiples = MultiplesPolicy::take_winner_of_goods;
  const auto want = serial(in, c);
  EXPECT_EQ(ex103::sort_parallel(in, c, 4), want);
  // Every cut is at a gap wider than the window, measured between accepted singles.
  const auto starts = ex103::slice_starts(in, c, 4);
  ASSERT_GE(starts.size(), 2U) << "the stream has some gaps";
  for (std::size_t s = 1; s < starts.size(); ++s) {
    const std::size_t i = starts[s];
    std::size_t prev = i;
    do {
      --prev;
    } while (prev > 0 && !(in[prev].energy.count() >= 435.0F && in[prev].energy.count() <= 585.0F));
    EXPECT_GT(in[i].time - in[prev].time, c.window) << "cut " << s;
  }
}

TEST(ParallelSorter, AWindowAcrossTheNominalCut) {
  // Four singles: a pair that straddles the middle, then a lone single.
  // Equal halves would split the pair; the delayed partner of the first
  // single sits in the second half.
  SorterConfig c;
  c.min_sector_difference = 0;
  const auto s = [](std::int64_t t, std::uint32_t x) { return Single{Picoseconds{t}, CrystalId{x}, KeV{511.0F}}; };
  const std::vector<Single> in{s(0, 1), s(2'000, 2), s(50'000, 3), s(101'000, 4)};
  const auto want = serial(in, c);
  ASSERT_EQ(want.size(), 2U) << "one prompt (0, 2 ns) and one delayed (0, 101 ns)";
  EXPECT_EQ(ex103::sort_parallel(in, c, 2), want);
}
