// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <vector>

#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/truth_counter.hpp"
#include "reference_sorter.hpp"

using namespace minidaq;
using ex101::Pair;

namespace {

Single at(std::int64_t t, float kev = 511.0F) { return Single{Picoseconds{t}, CrystalId{0}, KeV{kev}}; }

std::vector<sim::TruthSingle> simulate(double activity, double seconds) {
  sim::SimulatorConfig c;
  c.activity_bq = activity;
  c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  c.seed = 12;
  sim::DetectorSimulator d{c};
  return d.generate_until(Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
}

}  // namespace

TEST(ReferenceSorter, WindowsAreFixedAndMultiplesAreDiscarded) {
  const ex101::Rules r;
  EXPECT_EQ(ex101::sort_coincidences(std::vector<Single>{at(0), at(4'000)}, r), (std::vector<Pair>{{0, 1}}))
      << "the window is inclusive";
  EXPECT_TRUE(ex101::sort_coincidences(std::vector<Single>{at(0), at(1'000), at(2'000)}, r).empty())
      << "three singles in one window are a multiple";
  // 0 opens a window holding 3 ns; 6 ns opens the next one alone.
  EXPECT_EQ(ex101::sort_coincidences(std::vector<Single>{at(0), at(3'000), at(6'000)}, r), (std::vector<Pair>{{0, 1}}));
  // The 300 keV single takes no part: 0 and 2 form a pair.
  EXPECT_EQ(ex101::sort_coincidences(std::vector<Single>{at(0), at(1'000, 300.0F), at(2'000)}, r),
            (std::vector<Pair>{{0, 2}}));
}

TEST(ReferenceSorter, AgreesWithTheGroundTruthAndTheMiniDaqSorter) {
  const auto truth = simulate(10e6, 0.05);
  std::vector<Single> singles;
  for (const auto& t : truth) {
    singles.push_back(t.single);
  }
  const ex101::Rules r;
  const auto pairs = ex101::sort_coincidences(singles, r);
  const auto got = ex101::classify(truth, pairs);
  const auto want = sim::count_coincidences(truth, {r.window, r.energy_low_kev, r.energy_high_kev});
  EXPECT_EQ(got.trues, want.trues);
  EXPECT_EQ(got.scatters, want.scatters);
  EXPECT_EQ(got.randoms, want.randoms);
  EXPECT_GT(want.randoms, 100U);

  SorterConfig c;
  c.delay = Picoseconds{0};
  c.min_sector_difference = 0;
  CoincidenceSorter lib{c};
  std::vector<Coincidence> found;
  lib.push(singles, found);
  lib.flush(found);
  ASSERT_EQ(found.size(), pairs.size());
  for (std::size_t i = 0; i < pairs.size(); ++i) {
    ASSERT_EQ(found[i].first, singles[pairs[i].first]) << i;
    ASSERT_EQ(found[i].second, singles[pairs[i].second]) << i;
  }
}
