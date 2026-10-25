// SPDX-License-Identifier: MIT
// The coincidence sorter (Chapter 10): hand-made streams for each rule, then
// properties on simulated data: chunking does not matter, every single is
// accounted for, and the counts agree with the simulator's ground truth.
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/truth_counter.hpp"

using namespace minidaq;
using G = ScannerGeometry;

namespace {

constexpr std::int64_t ns = 1'000;

// A single at `t_ps` on transaxial crystal `t` of ring 0, 511 keV unless given.
Single at(std::int64_t t_ps, std::uint32_t transaxial, float kev = 511.0F) {
  return Single{Picoseconds{t_ps}, G::make_crystal(0, transaxial), KeV{kev}};
}

// Transaxial positions: sector = t / 16, opposite = t + 192.
constexpr std::uint32_t a0 = 0;
constexpr std::uint32_t opposite0 = 192;

SorterConfig plain() {
  SorterConfig c;
  c.delay = Picoseconds{0};
  c.min_sector_difference = 0;
  return c;
}

std::vector<Coincidence> run(const SorterConfig& c, const std::vector<Single>& in, SorterStats* stats = nullptr) {
  CoincidenceSorter s{c};
  std::vector<Coincidence> out;
  s.push(in, out);
  s.flush(out);
  if (stats != nullptr) {
    *stats = s.stats();
  }
  return out;
}

std::vector<sim::TruthSingle> simulate(double activity_bq, double seconds, std::uint64_t seed) {
  sim::SimulatorConfig c;
  c.activity_bq = activity_bq;
  c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  c.seed = seed;
  sim::DetectorSimulator d{c};
  return d.generate_until(Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
}

std::vector<Single> singles_of(const std::vector<sim::TruthSingle>& t) {
  std::vector<Single> s;
  s.reserve(t.size());
  for (const auto& x : t) {
    s.push_back(x.single);
  }
  return s;
}

}  // namespace

TEST(CoincidenceSorter, TheWindowIsInclusive) {
  // REQ: SRS-SRT-001
  const auto c = plain();
  EXPECT_EQ(run(c, {at(0, a0), at(4'000, opposite0)}).size(), 1U) << "exactly the window apart";
  SorterStats st;
  EXPECT_TRUE(run(c, {at(0, a0), at(4'001, opposite0)}, &st).empty()) << "1 ps too far";
  EXPECT_EQ(st.singles_alone, 2U);
  const auto pair = run(c, {at(10, a0), at(1'010, opposite0)});
  ASSERT_EQ(pair.size(), 1U);
  EXPECT_EQ(pair[0].first.time, Picoseconds{10}) << "first is the earlier single";
  EXPECT_EQ(pair[0].time_difference(), Picoseconds{1'000});
  EXPECT_EQ(pair[0].kind, CoincidenceKind::prompt);
}

TEST(CoincidenceSorter, FixedAndPerSingleWindowsDiffer) {
  // REQ: SRS-SRT-002
  // a, b 3 ns later, c 3 ns after b; window 4 ns. A fixed window opened by a
  // holds a and b, and c opens its own; per-single windows pair a-b and b-c.
  const std::vector<Single> chain{at(0, a0), at(3 * ns, opposite0), at(6 * ns, 96)};
  auto c = plain();
  EXPECT_EQ(run(c, chain).size(), 1U);
  c.mode = WindowMode::per_single;
  const auto both = run(c, chain);
  ASSERT_EQ(both.size(), 2U);
  EXPECT_EQ(both[0].second, both[1].first) << "b is used twice";

  // Three singles within one window: a fixed window sees one multiple; per
  // single, a sees the multiple and b still pairs with c.
  const std::vector<Single> triple{at(0, a0), at(1 * ns, opposite0), at(2 * ns, 96)};
  SorterStats st;
  c.mode = WindowMode::fixed;
  EXPECT_TRUE(run(c, triple, &st).empty()) << "kill_all";
  EXPECT_EQ(st.multiple_windows, 1U);
  c.mode = WindowMode::per_single;
  EXPECT_EQ(run(c, triple).size(), 1U);

  // Per single, a window's pairs all contain its opener, so no pair is found
  // twice: a's window gives a-b and a-c, b's window gives b-c.
  c.multiples = MultiplesPolicy::take_all_goods;
  const auto all = run(c, triple);
  ASSERT_EQ(all.size(), 3U);
  EXPECT_EQ(all[0].first.time, Picoseconds{0});
  EXPECT_EQ(all[1].first.time, Picoseconds{0});
  EXPECT_EQ(all[2].first.time, Picoseconds{1 * ns});
  EXPECT_EQ(all[2].second.time, Picoseconds{2 * ns});
}

TEST(CoincidenceSorter, MultiplesPolicies) {
  // REQ: SRS-SRT-003
  // Window of three: a (sector 0), b (sector 0, same block as a), c opposite.
  // Good pairs with min_sector_difference 1: a-c and b-c; a-b is not.
  const std::vector<Single> w{at(0, 0, 500.0F), at(1 * ns, 5, 520.0F), at(2 * ns, opposite0, 505.0F)};
  auto c = plain();
  c.min_sector_difference = 1;
  std::map<MultiplesPolicy, std::size_t> kept;
  for (auto p : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods, MultiplesPolicy::take_winner_of_goods,
                 MultiplesPolicy::keep_if_only_one_good}) {
    c.multiples = p;
    SorterStats st;
    const auto out = run(c, w, &st);
    kept[p] = out.size();
    if (p == MultiplesPolicy::take_winner_of_goods) {
      ASSERT_EQ(out.size(), 1U);
      EXPECT_EQ(out[0].first.energy, KeV{520.0F}) << "b-c has the highest summed energy";
    }
    EXPECT_EQ(st.prompts_from_multiples, out.size());
  }
  EXPECT_EQ(kept[MultiplesPolicy::kill_all], 0U);
  EXPECT_EQ(kept[MultiplesPolicy::take_all_goods], 2U);
  EXPECT_EQ(kept[MultiplesPolicy::take_winner_of_goods], 1U);
  EXPECT_EQ(kept[MultiplesPolicy::keep_if_only_one_good], 0U) << "two pairs are good";

  // Sectors 0, 1 and 2 with min_sector_difference 2: only the outer pair is good.
  c.min_sector_difference = 2;
  const std::vector<Single> span{at(0, 0), at(1 * ns, 20), at(2 * ns, 40)};
  for (auto p : {MultiplesPolicy::take_all_goods, MultiplesPolicy::take_winner_of_goods,
                 MultiplesPolicy::keep_if_only_one_good}) {
    c.multiples = p;
    const auto only = run(c, span);
    ASSERT_EQ(only.size(), 1U) << to_string(p);
    EXPECT_EQ(only[0].first.crystal, G::make_crystal(0, 0));
    EXPECT_EQ(only[0].second.crystal, G::make_crystal(0, 40));
  }
}

TEST(CoincidenceSorter, TiesKeepTheEarlierPair) {
  // REQ: SRS-SRT-012
  // Found by the sorter's FMEA (Chapter 15): a-b and b-c have the same summed
  // energy, and nothing fixed which one take_winner_of_goods keeps.
  auto c = plain();
  c.multiples = MultiplesPolicy::take_winner_of_goods;
  const std::vector<Single> w{at(0, 0, 500.0F), at(1 * ns, 96, 511.0F), at(2 * ns, opposite0, 500.0F)};
  const auto out = run(c, w);
  ASSERT_EQ(out.size(), 1U);
  EXPECT_EQ(out[0].first.time, Picoseconds{0});
  EXPECT_EQ(out[0].second.time, Picoseconds{1 * ns});
}

TEST(CoincidenceSorter, GeometryCuts) {
  // REQ: SRS-SRT-004
  auto c = plain();
  CoincidenceSorter any{c};
  EXPECT_TRUE(any.good(at(0, 0), at(0, 5)));
  c.min_sector_difference = 1;
  CoincidenceSorter sectors{c};
  EXPECT_FALSE(sectors.good(at(0, 0), at(0, 5))) << "same block";
  EXPECT_TRUE(sectors.good(at(0, 0), at(0, 16))) << "neighbouring blocks";
  EXPECT_TRUE(sectors.good(at(0, 0), at(0, 383))) << "the ring wraps: sector 23 is next to sector 0";
  c.min_sector_difference = 2;
  EXPECT_FALSE(CoincidenceSorter{c}.good(at(0, 0), at(0, 383)));
  // A quarter turn apart, the line of response passes r cos(45 deg) = 106 mm
  // from the axis; opposite crystals pass through it.
  c.min_sector_difference = 0;
  c.fov_radius_mm = 100.0;
  CoincidenceSorter fov100{c};
  EXPECT_TRUE(fov100.good(at(0, 0), at(0, opposite0)));
  EXPECT_FALSE(fov100.good(at(0, 0), at(0, 96)));
  EXPECT_FALSE(fov100.good(at(0, 0), at(0, 0))) << "same transaxial crystal: no line";
  c.fov_radius_mm = 110.0;
  EXPECT_TRUE(CoincidenceSorter{c}.good(at(0, 0), at(0, 96)));
  // Rings do not matter to either cut.
  EXPECT_TRUE(CoincidenceSorter{c}.good(Single{Picoseconds{0}, G::make_crystal(47, 0), KeV{511.0F}}, at(0, opposite0)));
}

TEST(CoincidenceSorter, EnergyGateAndOrder) {
  // REQ: SRS-SRT-005
  SorterConfig c = plain();
  SorterStats st;
  const auto nan = std::numeric_limits<float>::quiet_NaN();
  const auto out = run(c,
                       {at(0, 0, 434.0F), at(1, 1, 435.0F), at(2, opposite0, 585.0F), at(3, 2, 585.5F), at(4, 3, nan),
                        at(5 * ns, 4), at(4 * ns, 5)},
                       &st);
  EXPECT_EQ(out.size(), 1U) << "435 and 585 are inside";
  EXPECT_EQ(st.energy_rejected, 3U);
  EXPECT_EQ(st.out_of_order, 1U);
  EXPECT_EQ(st.singles_alone, 1U);
}

TEST(CoincidenceSorter, DelayedWindow) {
  // REQ: SRS-SRT-006
  SorterConfig c = plain();
  c.delay = Picoseconds{100 * ns};
  const auto d = [&](std::int64_t t) { return run(c, {at(0, a0), at(t, opposite0)}); };
  ASSERT_EQ(d(100 * ns).size(), 1U);
  EXPECT_EQ(d(100 * ns)[0].kind, CoincidenceKind::delayed);
  EXPECT_EQ(d(100 * ns + 4'000).size(), 1U) << "inclusive at delay + window";
  EXPECT_TRUE(d(100 * ns - 1).empty());
  EXPECT_TRUE(d(100 * ns + 4'001).empty());
  // A prompt pair and a delayed single: one prompt, one delayed (from the opener).
  SorterStats st;
  const auto mixed = run(c, {at(0, a0), at(1 * ns, opposite0), at(101 * ns, 100)}, &st);
  EXPECT_EQ(st.prompts, 1U);
  EXPECT_EQ(st.delayed, 1U);
  ASSERT_EQ(mixed.size(), 2U);
  EXPECT_EQ(mixed[1].first, mixed[0].first) << "the delayed window belongs to the prompt window's opener";
  // Two singles in the delayed window are a delayed multiple: kill_all drops
  // it. (The two singles are also a prompt pair of their own.)
  const std::vector<Single> two{at(0, a0), at(100 * ns, opposite0), at(101 * ns, 100)};
  (void)run(c, two, &st);
  EXPECT_EQ(st.delayed, 0U);
  EXPECT_EQ(st.prompts, 1U);
  c.multiples = MultiplesPolicy::take_all_goods;
  (void)run(c, two, &st);
  EXPECT_EQ(st.delayed, 2U);
}

TEST(CoincidenceSorter, RejectsBadConfigurations) {
  // REQ: SRS-SRT-007
  const auto nan = std::numeric_limits<double>::quiet_NaN();
  const auto bad = [](auto change) {
    SorterConfig c;
    change(c);
    return !validate(c);
  };
  EXPECT_FALSE(bad([](SorterConfig&) {}));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.window = Picoseconds{0}; }));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.window = Picoseconds{1'000'001}; }));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.delay = c.window; }));
  EXPECT_FALSE(bad([](SorterConfig& c) { c.delay = Picoseconds{0}; }));
  EXPECT_TRUE(bad([&](SorterConfig& c) { c.energy_low_kev = nan; }));
  EXPECT_TRUE(bad([&](SorterConfig& c) { c.energy_high_kev = nan; }));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.energy_low_kev = 600.0; }));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.min_sector_difference = 13; }));
  EXPECT_TRUE(bad([&](SorterConfig& c) { c.fov_radius_mm = nan; }));
  EXPECT_TRUE(bad([](SorterConfig& c) { c.fov_radius_mm = 150.0; }));
  SorterConfig c;
  c.window = Picoseconds{-1};
  EXPECT_THROW((void)CoincidenceSorter{c}, std::invalid_argument);
  for (auto p : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods, MultiplesPolicy::take_winner_of_goods,
                 MultiplesPolicy::keep_if_only_one_good}) {
    EXPECT_EQ(parse_multiples_policy(to_string(p)).value(), p);
  }
  EXPECT_EQ(parse_window_mode("per_single").value(), WindowMode::per_single);
  EXPECT_NE(parse_multiples_policy("keep_all").error().find("take_winner_of_goods"), std::string::npos);
}

TEST(CoincidenceSorter, ChunkingDoesNotChangeTheResult) {
  // REQ: SRS-SRT-008
  const auto singles = singles_of(simulate(20e6, 0.002, 7));
  ASSERT_GT(singles.size(), 10'000U);
  std::mt19937_64 rng{3};
  for (auto mode : {WindowMode::fixed, WindowMode::per_single}) {
    for (auto p : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods, MultiplesPolicy::take_winner_of_goods,
                   MultiplesPolicy::keep_if_only_one_good}) {
      SorterConfig c;
      c.mode = mode;
      c.multiples = p;
      c.fov_radius_mm = 120.0;
      SorterStats whole_stats;
      const auto whole = run(c, singles, &whole_stats);
      CoincidenceSorter s{c};
      std::vector<Coincidence> pieces;
      std::size_t i = 0;
      while (i < singles.size()) {
        const std::size_t n = std::min<std::size_t>(singles.size() - i, std::uniform_int_distribution<std::size_t>{0, 300}(rng));
        s.push(std::span{singles}.subspan(i, n), pieces);
        i += n;
      }
      s.flush(pieces);
      EXPECT_EQ(pieces, whole) << to_string(mode) << " " << to_string(p);
      EXPECT_EQ(s.stats(), whole_stats);
      EXPECT_GT(whole_stats.delayed, 0U);
    }
  }
}

TEST(CoincidenceSorter, EverySingleIsAccountedFor) {
  // REQ: SRS-SRT-009
  const auto singles = singles_of(simulate(20e6, 0.002, 8));
  SorterConfig c;
  c.multiples = MultiplesPolicy::take_all_goods;
  SorterStats st;
  const auto out = run(c, singles, &st);
  EXPECT_EQ(st.singles_in, singles.size());
  EXPECT_EQ(st.singles_in,
            st.energy_rejected + st.out_of_order + st.singles_alone + 2 * st.pair_windows + st.singles_in_multiples);
  EXPECT_EQ(st.prompts + st.delayed, out.size());
  EXPECT_GT(st.prompts_from_multiples, 0U);
  EXPECT_LE(st.prompts - st.prompts_from_multiples, st.pair_windows);
  // With kill_all only clean pairs are judged: each is a prompt or rejected.
  c.multiples = MultiplesPolicy::kill_all;
  SorterStats k;
  (void)run(c, singles, &k);
  EXPECT_EQ(k.pair_windows, k.prompts + k.geometry_rejected);
  EXPECT_EQ(k.prompts_from_multiples, 0U);
  EXPECT_GT(k.geometry_rejected, 0U);
  for (const auto& x : out) {
    const auto dt = x.time_difference();
    if (x.kind == CoincidenceKind::prompt) {
      EXPECT_GE(dt, Picoseconds{0});
      EXPECT_LE(dt, c.window);
    } else {
      EXPECT_GE(dt, c.delay);
      EXPECT_LE(dt, c.delay + c.window);
    }
  }
  EXPECT_TRUE(std::is_sorted(out.begin(), out.end(), [](const Coincidence& a, const Coincidence& b) {
    return a.first.time < b.first.time;
  })) << "coincidences come out in the order of their openers";
}

TEST(CoincidenceSorter, MatchesTheSimulatorsGroundTruth) {
  // REQ: SRS-SRT-010
  // Configured like the Chapter 8 reference counter (fixed window, kill_all,
  // no geometry cuts), the sorter must find exactly the same prompts.
  const auto truth = simulate(5e6, 0.05, 9);
  SorterConfig c = plain();
  SorterStats st;
  const auto out = run(c, singles_of(truth), &st);
  const auto ref = sim::count_coincidences(truth, {c.window, c.energy_low_kev, c.energy_high_kev});
  EXPECT_EQ(st.singles_in - st.energy_rejected, ref.singles);
  EXPECT_EQ(st.prompts, ref.prompts());
  EXPECT_EQ(st.multiple_windows, ref.multiples);
  EXPECT_GT(ref.trues, 1000U);
  EXPECT_EQ(out.size(), ref.prompts());
}

// Randoms among the prompts, by truth: the two singles come from different decays.
std::uint64_t true_randoms(const std::vector<sim::TruthSingle>& truth, const std::vector<Coincidence>& found) {
  std::map<std::pair<std::int64_t, std::uint32_t>, std::uint64_t> decay;
  for (const auto& t : truth) {
    decay[{t.single.time.count(), t.single.crystal.value()}] = t.decay;
  }
  std::uint64_t n = 0;
  for (const auto& c : found) {
    if (c.kind == CoincidenceKind::prompt &&
        decay.at({c.first.time.count(), c.first.crystal.value()}) !=
            decay.at({c.second.time.count(), c.second.crystal.value()})) {
      ++n;
    }
  }
  return n;
}

TEST(CoincidenceSorter, TheDelayedWindowEstimateDependsOnTheMultiplesPolicy) {
  // REQ: SRS-SRT-011
  // At 40 MBq about 30% of the prompts are randoms. The delayed window counts
  // them to within 15%, but not exactly, and the error depends on the
  // multiples policy: with kill_all a random that shares its window with a
  // true pair is killed in the prompts but still counted in the delayed
  // window; take_all_goods keeps such randoms twice over (two pairs per
  // triple). measurements/ch10/validation.txt has the numbers. Each bias alone
  // is a few standard deviations; their difference is about seven.
  const auto truth = simulate(40e6, 0.05, 10);
  const auto singles = singles_of(truth);
  SorterConfig c = plain();
  c.delay = Picoseconds{100 * ns};
  double bias[2] = {};
  double variance = 0.0;
  int k = 0;
  for (auto p : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods}) {
    c.multiples = p;
    SorterStats st;
    const auto found = run(c, singles, &st);
    const auto randoms = static_cast<double>(true_randoms(truth, found));
    const auto delayed = static_cast<double>(st.delayed);
    ASSERT_GT(randoms, 5'000.0);
    EXPECT_LT(std::abs(delayed - randoms), 0.15 * randoms) << to_string(p) << ": delayed " << delayed << ", randoms " << randoms;
    bias[k++] = delayed - randoms;
    variance += delayed + randoms;
  }
  EXPECT_GT(bias[0] - bias[1], 4.0 * std::sqrt(variance))
      << "kill_all overestimates relative to take_all_goods: " << bias[0] << " vs " << bias[1];
}
