// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <cmath>
#include <cstdint>
#include <random>
#include <thread>
#include <vector>

#include "minidaq/processing/timing_monitor.hpp"

using minidaq::BlockOffsets;
using minidaq::Coincidence;
using minidaq::CoincidenceKind;
using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::PairShift;
using minidaq::Picoseconds;
using minidaq::ScannerGeometry;
using minidaq::Single;
using minidaq::solve_block_offsets;
using minidaq::TimingLevel;
using minidaq::TimingMonitor;
using minidaq::TimingMonitorConfig;
using minidaq::TimingSnapshot;

namespace {

constexpr std::int64_t second_ps = 1'000'000'000'000;
constexpr std::int64_t delay_ps = 100'000;
constexpr std::int64_t window_ps = 4'000;

// A crystal in the middle of a block.
CrystalId crystal_of_block(std::uint32_t block) {
  const std::uint32_t ring = (block / ScannerGeometry::blocks_per_ring) * 16 + 8;
  const std::uint32_t trans = (block % ScannerGeometry::blocks_per_ring) * 16 + 8;
  return ScannerGeometry::make_crystal(ring, trans);
}

// A coincidence of blocks a and b at time t whose difference t_b - t_a is d (prompt) or
// d + the delay (delayed): the earlier single comes first, as the sorter emits them.
Coincidence pair(std::uint32_t a, std::uint32_t b, std::int64_t t, std::int64_t d, bool delayed) {
  const std::int64_t shift = delayed ? delay_ps : 0;
  Single sa{Picoseconds{t}, crystal_of_block(a), KeV{511.0F}};
  Single sb{Picoseconds{t + d + shift}, crystal_of_block(b), KeV{511.0F}};
  const auto kind = delayed ? CoincidenceKind::delayed : CoincidenceKind::prompt;
  if (d + shift >= 0) {
    return Coincidence{sa, sb, kind};
  }
  sb.time = Picoseconds{t};
  sa.time = Picoseconds{t - d};
  return Coincidence{sb, sa, kind};
}

// Scanner data with a clock error per block: block k's time stamps are late by error(k, t).
// Each block pairs with the five blocks around the opposite one, in every block ring, so the
// blocks form one connected group, as a source in the scanner's center gives. Randoms make a flat
// distribution over the window, and the delayed window counts as many of them.
struct Scan {
  std::mt19937_64 rng{7};
  double trues_per_s = 100'000.0;
  double randoms_fraction = 0.3;
  double spread_ps = 200.0;  // the trues' time difference: resolution and geometry

  template <typename Error>
  std::vector<Coincidence> second(std::int64_t start_ps, Error error) {
    std::vector<Coincidence> out;
    std::uniform_int_distribution<std::uint32_t> block(0, ScannerGeometry::num_blocks - 1);
    std::uniform_int_distribution<int> fan(-2, 2);
    std::uniform_int_distribution<std::uint32_t> ring(0, ScannerGeometry::block_rings - 1);
    std::normal_distribution<double> spread(0.0, spread_ps);
    std::uniform_real_distribution<double> flat(-static_cast<double>(window_ps),
                                                static_cast<double>(window_ps));
    const auto n = static_cast<std::size_t>(trues_per_s * (1.0 + randoms_fraction));
    const auto randoms = static_cast<std::size_t>(trues_per_s * randoms_fraction);
    const double step = static_cast<double>(second_ps) / static_cast<double>(n + randoms);
    double t = static_cast<double>(start_ps);
    for (std::size_t i = 0; i < n + randoms; ++i, t += step) {
      const std::uint32_t a = block(rng);
      const auto per_ring = static_cast<int>(ScannerGeometry::blocks_per_ring);
      const int opposite = (static_cast<int>(a % ScannerGeometry::blocks_per_ring) + per_ring / 2 +
                            fan(rng) + per_ring) %
                           per_ring;
      const std::uint32_t b =
          ring(rng) * ScannerGeometry::blocks_per_ring + static_cast<std::uint32_t>(opposite);
      const auto ti = static_cast<std::int64_t>(t);
      const bool is_random = i >= n - randoms;  // the last randoms of n are prompt randoms
      const bool delayed = i >= n;
      double d = 0.0;
      if (delayed || is_random) {
        d = flat(rng);
      } else {
        d = spread(rng) + error(b, ti) - error(a, ti);
      }
      // A random's time difference does not depend on the clocks: the window is uniform anyway.
      out.push_back(pair(a, b, ti, static_cast<std::int64_t>(std::llround(d)), delayed));
    }
    return out;
  }
};

TimingMonitorConfig config() {
  TimingMonitorConfig c;
  c.delay = Picoseconds{delay_ps};
  return c;
}

}  // namespace

TEST(BlockOffsets, ExactShiftsGiveTheOffsetsWithAMeanOfZero) {
  // REQ: SRS-TIM-002
  // Offsets 0, 100, -50, 250 on a chain and a cycle of four blocks.
  const std::vector<double> truth{0.0, 100.0, -50.0, 250.0};
  std::vector<PairShift> pairs;
  for (auto [a, b] : {std::pair{0U, 1U}, {1U, 2U}, {2U, 3U}, {0U, 3U}, {0U, 2U}}) {
    pairs.push_back(PairShift{a, b, truth[b] - truth[a], 100.0});
  }
  const BlockOffsets fit = solve_block_offsets(4, pairs);
  const double mean = (0.0 + 100.0 - 50.0 + 250.0) / 4.0;
  for (std::size_t k = 0; k < 4; ++k) {
    EXPECT_NEAR(fit.offset_ps[k], truth[k] - mean, 1e-9) << k;
    EXPECT_TRUE(fit.observed[k]);
    EXPECT_GT(fit.sigma_ps[k], 0.0);
  }
  EXPECT_EQ(fit.groups, 1U);
  EXPECT_EQ(fit.dof, 2U);  // five pairs, three unknowns
  EXPECT_NEAR(fit.chi2, 0.0, 1e-9);
}

TEST(BlockOffsets, ASingleChainHasTheUncertaintyOfItsPairs) {
  // REQ: SRS-TIM-002
  // Two blocks, one pair of variance v: the offsets are -s/2 and +s/2, each of variance v/4.
  const std::vector<PairShift> pairs{{0, 1, 300.0, 400.0}};
  const BlockOffsets fit = solve_block_offsets(2, pairs);
  EXPECT_NEAR(fit.offset_ps[0], -150.0, 1e-9);
  EXPECT_NEAR(fit.offset_ps[1], 150.0, 1e-9);
  EXPECT_NEAR(fit.sigma_ps[0], 10.0, 1e-9);
  EXPECT_EQ(fit.dof, 0U);
}

TEST(BlockOffsets, GroupsAreSolvedApartAndALoneBlockIsUnobserved) {
  // REQ: SRS-TIM-002
  const std::vector<PairShift> pairs{{0, 1, 40.0, 1.0}, {2, 3, -20.0, 1.0}, {3, 4, -20.0, 1.0}};
  const BlockOffsets fit = solve_block_offsets(6, pairs);
  EXPECT_EQ(fit.groups, 2U);
  EXPECT_NEAR(fit.offset_ps[0] + fit.offset_ps[1], 0.0, 1e-9);
  EXPECT_NEAR(fit.offset_ps[1] - fit.offset_ps[0], 40.0, 1e-9);
  EXPECT_NEAR(fit.offset_ps[2] + fit.offset_ps[3] + fit.offset_ps[4], 0.0, 1e-9);
  EXPECT_NEAR(fit.offset_ps[4] - fit.offset_ps[2], -40.0, 1e-9);
  EXPECT_FALSE(fit.observed[5]);
  EXPECT_EQ(fit.offset_ps[5], 0.0);
}

TEST(BlockOffsets, ShiftsThatNoBlockClockExplainsGiveALargeChi2) {
  // REQ: SRS-TIM-002
  // A triangle whose shifts do not add up: 0->1 +100, 1->2 +100, 0->2 -200.
  const std::vector<PairShift> pairs{
      {0, 1, 100.0, 100.0}, {1, 2, 100.0, 100.0}, {0, 2, -200.0, 100.0}};
  const BlockOffsets fit = solve_block_offsets(3, pairs);
  EXPECT_EQ(fit.dof, 1U);
  EXPECT_GT(fit.chi2 / fit.dof, 100.0);
}

TEST(BlockOffsets, PairsThatCannotBeUsedAreLeftOut) {
  // REQ: SRS-TIM-002
  // The chain of two blocks above, with pairs that carry no measurement: a variance that is not
  // positive or not a number, a block paired with itself, a block beyond the scanner's.
  const std::vector<PairShift> pairs{{0, 1, 300.0, 400.0},        {0, 1, 900.0, 0.0},
                                     {0, 1, 900.0, std::nan("")}, {1, 1, 900.0, 1.0},
                                     {0, 2, 900.0, 1.0},          {2, 1, 900.0, 1.0}};
  const BlockOffsets fit = solve_block_offsets(2, pairs);
  EXPECT_NEAR(fit.offset_ps[0], -150.0, 1e-9);
  EXPECT_NEAR(fit.offset_ps[1], 150.0, 1e-9);
  EXPECT_NEAR(fit.sigma_ps[0], 10.0, 1e-9);
  EXPECT_EQ(fit.dof, 0U);
  EXPECT_NEAR(fit.chi2, 0.0, 1e-9);
}

TEST(TimingMonitor, NamesEachLevel) {
  // REQ: SRS-TIM-004
  EXPECT_EQ(minidaq::to_string(TimingLevel::unobserved), "unobserved");
  EXPECT_EQ(minidaq::to_string(TimingLevel::normal), "normal");
  EXPECT_EQ(minidaq::to_string(TimingLevel::warning), "warning");
  EXPECT_EQ(minidaq::to_string(TimingLevel::alarm), "alarm");
}

TEST(TimingMonitor, IgnoresCoincidencesWithinOneBlockOrOfACrystalThatDoesNotExist) {
  // REQ: SRS-TIM-001
  // The same scan twice, once with a coincidence within one block and one of a crystal beyond
  // the scanner after every coincidence: the two monitors see the same pairs and offsets.
  TimingMonitor plain{config()};
  TimingMonitor mixed{config()};
  Scan scan;
  const CrystalId nowhere{ScannerGeometry::num_crystals};
  for (int s = 0; s < 4; ++s) {
    const auto found = scan.second(
        s * second_ps, [](std::uint32_t b, std::int64_t) { return b == 3 ? 400.0 : 0.0; });
    std::vector<Coincidence> with;
    for (const Coincidence& c : found) {
      with.push_back(c);
      Coincidence same = c;
      same.second.crystal = c.first.crystal;
      with.push_back(same);
      Coincidence bad = c;
      bad.second.crystal = nowhere;
      with.push_back(bad);
    }
    plain.record(found);
    mixed.record(with);
  }
  plain.flush();
  mixed.flush();
  const TimingSnapshot a = plain.snapshot();
  const TimingSnapshot b = mixed.snapshot();
  EXPECT_GT(a.pairs, 0U);
  EXPECT_EQ(a.pairs, b.pairs);
  EXPECT_EQ(a.intervals, b.intervals);
  for (std::size_t k = 0; k < a.blocks.size(); ++k) {
    EXPECT_EQ(a.blocks[k].offset_ps, b.blocks[k].offset_ps) << k;
  }
}

TEST(TimingMonitor, RefusesAConfigurationThatCannotWork) {
  // REQ: SRS-TIM-001
  for (auto change : {+[](TimingMonitorConfig& c) { c.interval = Picoseconds{0}; },
                      +[](TimingMonitorConfig& c) { c.baseline_intervals = 0; },
                      +[](TimingMonitorConfig& c) { c.min_trues = 0.5; },
                      +[](TimingMonitorConfig& c) { c.warning_ps = 0.0; },
                      +[](TimingMonitorConfig& c) { c.alarm_ps = c.warning_ps - 1.0; },
                      +[](TimingMonitorConfig& c) { c.significance = -1.0; },
                      +[](TimingMonitorConfig& c) { c.half_window = Picoseconds{0}; },
                      +[](TimingMonitorConfig& c) { c.delay = Picoseconds{-1}; }}) {
    TimingMonitorConfig c;
    change(c);
    EXPECT_FALSE(minidaq::validate(c).has_value());
    EXPECT_THROW(TimingMonitor{c}, std::invalid_argument);
  }
  EXPECT_TRUE(minidaq::validate(TimingMonitorConfig{}).has_value());
}

TEST(TimingMonitor, AHealthyRunStaysNormalInEveryBlock) {
  // REQ: SRS-TIM-001, SRS-TIM-003
  TimingMonitor m{config()};
  Scan scan;
  for (int s = 0; s < 12; ++s) {
    m.record(scan.second(s * second_ps, [](std::uint32_t, std::int64_t) { return 0.0; }));
  }
  m.flush();
  const TimingSnapshot snap = m.snapshot();
  EXPECT_TRUE(snap.baseline_done);
  EXPECT_GE(snap.intervals, 11U);
  EXPECT_EQ(snap.groups, 1U);
  EXPECT_EQ(snap.alarm_intervals, 0U);
  EXPECT_EQ(snap.level, TimingLevel::normal);
  EXPECT_LT(snap.chi2_per_dof, 1.5);
  for (const auto& b : snap.blocks) {
    EXPECT_EQ(b.level, TimingLevel::normal);
    EXPECT_LT(std::abs(b.offset_ps), 5.0 * b.sigma_ps + 1.0);
  }
}

TEST(TimingMonitor, AStepInOneBlockClockIsFoundInThatBlockAndNoOther) {
  // REQ: SRS-TIM-001, SRS-TIM-002, SRS-TIM-003
  TimingMonitor m{config()};
  Scan scan;
  const std::uint32_t faulty = 29;
  const std::int64_t step_at = 5 * second_ps;  // the PLL relocks 500 ps away
  const auto error = [&](std::uint32_t k, std::int64_t t) {
    return k == faulty && t >= step_at ? 500.0 : 0.0;
  };
  for (int s = 0; s < 8; ++s) {
    m.record(scan.second(s * second_ps, error));
  }
  m.flush();
  const TimingSnapshot snap = m.snapshot();
  EXPECT_EQ(snap.level, TimingLevel::alarm);
  const auto& f = snap.blocks[faulty];
  EXPECT_EQ(f.level, TimingLevel::alarm);
  // The offsets have a mean of zero: the faulty block carries 500 * 71/72 of the step.
  EXPECT_NEAR(f.offset_ps, 500.0 * 71.0 / 72.0, 5.0 * f.sigma_ps + 5.0);
  EXPECT_EQ(f.alarm_intervals, 3U);  // seconds 5, 6 and 7
  EXPECT_GE(f.first_alarm_ps, 6 * second_ps);
  EXPECT_LE(f.first_alarm_ps, 7 * second_ps);  // the end of the first interval after the step
  for (std::size_t k = 0; k < snap.blocks.size(); ++k) {
    if (k != faulty) {
      EXPECT_NE(snap.blocks[k].level, TimingLevel::alarm) << k;
    }
  }
  EXPECT_LT(snap.chi2_per_dof, 1.5) << "a block's clock explains the shifts";
}

TEST(TimingMonitor, TheRandomsDoNotDiluteTheShift) {
  // REQ: SRS-TIM-002
  // Half the prompts are randoms: without the delayed window's subtraction the mean of the
  // prompts would move by half the step only.
  TimingMonitor m{config()};
  Scan scan;
  scan.randoms_fraction = 1.0;
  const auto error = [](std::uint32_t k, std::int64_t t) {
    return k == 3 && t >= 3 * second_ps ? 400.0 : 0.0;
  };
  for (int s = 0; s < 5; ++s) {
    m.record(scan.second(s * second_ps, error));
  }
  m.flush();
  const auto f = m.snapshot().blocks[3];
  EXPECT_NEAR(f.offset_ps, 400.0 * 71.0 / 72.0, 5.0 * f.sigma_ps + 5.0);
}

TEST(TimingMonitor, ADriftIsFoundOnceItPassesTheLimits) {
  // REQ: SRS-TIM-003
  TimingMonitor m{config()};
  Scan scan;
  // 60 ps per second on block 50 from the start. The baseline's 2 s average 60 ps, interval k
  // averages 60 (k + 0.5), so the offset is 60 k - 30 times 71/72 (the mean of zero): 148 ps in
  // interval 3, in the middle of the warning band, and 266 ps in interval 5, just above the alarm
  // limit, so the first alarm is in interval 5 or, with the statistics of one interval, 6.
  const auto error = [](std::uint32_t k, std::int64_t t) {
    return k == 50 ? 60.0 * static_cast<double>(t) / static_cast<double>(second_ps) : 0.0;
  };
  TimingLevel at_3 = TimingLevel::unobserved;
  for (int s = 0; s < 10; ++s) {
    m.record(scan.second(s * second_ps, error));
    if (s == 4) {
      at_3 = m.snapshot().blocks[50].level;  // the interval of second 3 is published
    }
  }
  m.flush();
  EXPECT_EQ(at_3, TimingLevel::warning);
  const auto f = m.snapshot().blocks[50];
  EXPECT_EQ(f.level, TimingLevel::alarm);
  EXPECT_GE(f.first_alarm_ps, 6 * second_ps);
  EXPECT_LE(f.first_alarm_ps, 7 * second_ps);
}

TEST(TimingMonitor, TooFewTruesLeaveTheBlocksUnobserved) {
  // REQ: SRS-TIM-003
  TimingMonitorConfig c = config();
  c.min_trues = 1e6;
  TimingMonitor m{c};
  Scan scan;
  for (int s = 0; s < 4; ++s) {
    m.record(scan.second(s * second_ps, [](std::uint32_t, std::int64_t) { return 0.0; }));
  }
  m.flush();
  const TimingSnapshot snap = m.snapshot();
  EXPECT_EQ(snap.pairs, 0U);
  EXPECT_EQ(snap.level, TimingLevel::unobserved);
}

TEST(TimingMonitor, ASnapshotCanBeTakenWhileTheMonitorRecords) {
  // REQ: SRS-TIM-001
  TimingMonitor m{config()};
  Scan scan;
  scan.trues_per_s = 50'000.0;
  std::vector<std::vector<Coincidence>> data;
  for (int s = 0; s < 6; ++s) {
    data.push_back(scan.second(s * second_ps, [](std::uint32_t, std::int64_t) { return 0.0; }));
  }
  std::atomic<bool> done{false};
  // threads: joined
  std::thread reader{[&] {
    while (!done.load()) {
      (void)m.snapshot();
    }
  }};
  for (const auto& d : data) {
    for (std::size_t i = 0; i < d.size(); i += 512) {
      m.record(
          std::span<const Coincidence>{d}.subspan(i, std::min<std::size_t>(512, d.size() - i)));
    }
  }
  m.flush();
  done = true;
  reader.join();
  EXPECT_GE(m.snapshot().intervals, 5U);
}
