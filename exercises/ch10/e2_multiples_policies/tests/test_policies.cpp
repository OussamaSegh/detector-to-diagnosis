// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <map>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "policies.hpp"

using namespace minidaq;
using ex102::Pair;

namespace {

constexpr MultiplesPolicy all_policies[] = {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods,
                                            MultiplesPolicy::take_winner_of_goods,
                                            MultiplesPolicy::keep_if_only_one_good};

Single at(std::int64_t t, std::uint32_t transaxial, float kev = 511.0F) {
  return Single{Picoseconds{t}, ScannerGeometry::make_crystal(0, transaxial), KeV{kev}};
}

// Singles inside 435-585 keV from the simulator.
std::vector<Single> simulated(double activity, double seconds) {
  sim::SimulatorConfig c;
  c.activity_bq = activity;
  c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  c.seed = 13;
  sim::DetectorSimulator d{c};
  std::vector<Single> v;
  for (const auto& t : d.generate_until(Picoseconds{static_cast<std::int64_t>(seconds * 1e12)})) {
    if (t.single.energy.count() >= 435.0F && t.single.energy.count() <= 585.0F) {
      v.push_back(t.single);
    }
  }
  // Singles with equal times in crystal order, as MiniDAQ's sorter takes them (SRS-SRT-013).
  std::stable_sort(v.begin(), v.end(), [](const auto& a, const auto& b) {
    return a.time != b.time ? a.time < b.time : a.crystal < b.crystal;
  });
  return v;
}

}  // namespace

TEST(MultiplesPolicies, OneWindowByHand) {
  // a and b in sector 0, c opposite: with "different sectors" as the rule,
  // a-c and b-c are good, a-b is not. b-c has the highest summed energy.
  SorterConfig cfg;
  cfg.min_sector_difference = 1;
  const CoincidenceSorter rules{cfg};
  const ex102::Good good = [&](const Single& x, const Single& y) { return rules.good(x, y); };
  const std::vector<Single> w{at(0, 0, 500.0F), at(1'000, 5, 520.0F), at(2'000, 192, 505.0F)};
  EXPECT_TRUE(ex102::resolve(w, MultiplesPolicy::kill_all, good).empty());
  EXPECT_EQ(ex102::resolve(w, MultiplesPolicy::take_all_goods, good), (std::vector<Pair>{{0, 2}, {1, 2}}));
  EXPECT_EQ(ex102::resolve(w, MultiplesPolicy::take_winner_of_goods, good), (std::vector<Pair>{{1, 2}}));
  EXPECT_TRUE(ex102::resolve(w, MultiplesPolicy::keep_if_only_one_good, good).empty());
  const std::vector<Single> one{at(0, 0), at(1'000, 5), at(2'000, 10), at(3'000, 192)};
  // Everything in sector 0 except the last: three good pairs. Make only one good:
  const ex102::Good only_last_two = [](const Single& x, const Single& y) {
    return x.time == Picoseconds{2'000} && y.time == Picoseconds{3'000};
  };
  EXPECT_EQ(ex102::resolve(one, MultiplesPolicy::keep_if_only_one_good, only_last_two), (std::vector<Pair>{{2, 3}}));
  EXPECT_EQ(ex102::resolve(one, MultiplesPolicy::take_winner_of_goods, only_last_two), (std::vector<Pair>{{2, 3}}));
  const ex102::Good none = [](const Single&, const Single&) { return false; };
  for (auto p : all_policies) {
    EXPECT_TRUE(ex102::resolve(one, p, none).empty()) << to_string(p);
  }
  // A tie in energy keeps the first good pair.
  const std::vector<Single> tie{at(0, 0), at(1'000, 100), at(2'000, 200)};
  const ex102::Good any = [](const Single&, const Single&) { return true; };
  EXPECT_EQ(ex102::resolve(tie, MultiplesPolicy::take_winner_of_goods, any), (std::vector<Pair>{{0, 1}}));
}

TEST(MultiplesPolicies, MatchMiniDaqAndOrderAsExpected) {
  for (double activity : {5e6, 30e6}) {
    const auto singles = simulated(activity, 0.01);
    SorterConfig cfg;
    cfg.delay = Picoseconds{0};
    cfg.min_sector_difference = 1;
    cfg.fov_radius_mm = 120.0;
    std::map<MultiplesPolicy, std::size_t> n;
    for (auto p : all_policies) {
      cfg.multiples = p;
      CoincidenceSorter lib{cfg};
      const ex102::Good good = [&](const Single& x, const Single& y) { return lib.good(x, y); };
      const auto mine = ex102::sort_with(singles, cfg.window, p, good);
      std::vector<Coincidence> want;
      lib.push(singles, want);
      lib.flush(want);
      EXPECT_EQ(mine, want) << to_string(p) << " at " << activity;
      n[p] = mine.size();
    }
    // Each policy keeps at least what the next keeps, by construction.
    EXPECT_GE(n[MultiplesPolicy::take_all_goods], n[MultiplesPolicy::take_winner_of_goods]);
    EXPECT_GE(n[MultiplesPolicy::take_winner_of_goods], n[MultiplesPolicy::keep_if_only_one_good]);
    EXPECT_GE(n[MultiplesPolicy::keep_if_only_one_good], n[MultiplesPolicy::kill_all]);
    EXPECT_GT(n[MultiplesPolicy::take_all_goods], n[MultiplesPolicy::kill_all]) << "multiples exist at " << activity;
  }
}
