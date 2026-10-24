// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <random>
#include <vector>

#include "dead_time.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/sim/dead_time.hpp"

using namespace minidaq;
using ex112::Model;

namespace {

using G = ScannerGeometry;
constexpr std::int64_t ns = 1'000;
constexpr Picoseconds tau100{100 * ns};

// Transaxial positions 0 to 15 are block 0, 16 to 31 block 1.
sim::TruthSingle at(std::int64_t t, std::uint32_t transaxial = 0, float kev = 511.0F) {
  return sim::TruthSingle{Single{Picoseconds{t}, G::make_crystal(0, transaxial), KeV{kev}}, 0, 0, false};
}

std::vector<std::int64_t> times(const ex112::Result& r) {
  std::vector<std::int64_t> t;
  for (const auto& x : r.recorded) {
    t.push_back(x.single.time.count());
  }
  return t;
}

}  // namespace

TEST(DeadTime, NonParalyzable) {
  // 50 ns is lost and does not extend; 120 ns is recorded; 220 ns arrives
  // exactly when the block is free again.
  const auto r = ex112::apply_dead_time(std::vector{at(0), at(50 * ns, 3), at(120 * ns), at(220 * ns)},
                                        Model::non_paralyzable, tau100, false);
  EXPECT_EQ(times(r), (std::vector<std::int64_t>{0, 120 * ns, 220 * ns}));
  EXPECT_EQ(r.lost, 1U);
}

TEST(DeadTime, Paralyzable) {
  // Every arrival restarts the 100 ns: only 0 and 320 ns are recorded.
  const auto r = ex112::apply_dead_time(std::vector{at(0), at(50 * ns), at(120 * ns), at(320 * ns)},
                                        Model::paralyzable, tau100, false);
  EXPECT_EQ(times(r), (std::vector<std::int64_t>{0, 320 * ns}));
  EXPECT_EQ(r.lost, 2U);
}

TEST(DeadTime, BlocksAreIndependent) {
  const auto r = ex112::apply_dead_time(std::vector{at(0, 0), at(10 * ns, 16), at(20 * ns, 1)},
                                        Model::non_paralyzable, tau100, false);
  EXPECT_EQ(times(r), (std::vector<std::int64_t>{0, 10 * ns})) << "16 is in block 1; 1 is in block 0";
}

TEST(DeadTime, PileUpAddsTheEnergy) {
  for (const auto m : {Model::non_paralyzable, Model::paralyzable}) {
    const auto r = ex112::apply_dead_time(std::vector{at(0, 0, 511.0F), at(30 * ns, 2, 200.0F), at(60 * ns, 16, 511.0F)},
                                          m, tau100, true);
    ASSERT_EQ(r.recorded.size(), 2U);
    EXPECT_FLOAT_EQ(r.recorded[0].single.energy.count(), 711.0F);
    EXPECT_FLOAT_EQ(r.recorded[1].single.energy.count(), 511.0F) << "block 1 is not affected";
    EXPECT_EQ(r.piled_up, 1U);
  }
}

TEST(DeadTime, RatesFollowTheModels) {
  // Poisson arrivals at 5 M/s on one block with tau = 100 ns (n tau = 0.5).
  // About 300,000 recorded events: a relative standard deviation near 0.2%,
  // so 1% is about five of them.
  std::mt19937_64 rng{3};
  std::exponential_distribution<double> gap{5e6 * 1e-12};
  std::vector<sim::TruthSingle> in;
  for (double t = gap(rng); t < 0.1e12; t += gap(rng)) {
    in.push_back(at(static_cast<std::int64_t>(t), static_cast<std::uint32_t>(in.size() % 16)));
  }
  const double offered = static_cast<double>(in.size()) / 0.1;
  for (const auto m : {Model::non_paralyzable, Model::paralyzable}) {
    const auto r = ex112::apply_dead_time(in, m, tau100, false);
    const double measured = static_cast<double>(r.recorded.size()) / 0.1;
    EXPECT_NEAR(measured / ex112::recorded_rate(m, offered, 100e-9), 1.0, 0.01);
    EXPECT_EQ(r.recorded.size() + r.lost, in.size());
  }
  EXPECT_NEAR(ex112::recorded_rate(Model::non_paralyzable, 5e6, 100e-9), 5e6 / 1.5, 1e-6);
  EXPECT_NEAR(ex112::recorded_rate(Model::paralyzable, 1e7, 100e-9), 1e7 / std::exp(1.0), 1e-6);
}

TEST(DeadTime, MatchesMiniDaqOnSimulatedData) {
  sim::DetectorSimulator d{{.activity_bq = 30e6,
                            .source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0},
                            .phantom = {90.0, 180.0},
                            .seed = 8}};
  const auto in = d.generate_until(Picoseconds{3'000'000'000});  // 3 ms
  for (const auto m : {Model::non_paralyzable, Model::paralyzable}) {
    const auto mine = ex112::apply_dead_time(in, m, Picoseconds{1'000 * ns}, true);
    sim::DeadTime ref{{m == Model::paralyzable ? sim::DeadTimeModel::paralyzable : sim::DeadTimeModel::non_paralyzable,
                       sim::DeadTimeUnit::block, Picoseconds{1'000 * ns}, true}};
    std::vector<sim::TruthSingle> expected;
    ref.push(in, expected);
    ref.flush(expected);
    ASSERT_EQ(mine.recorded.size(), expected.size());
    for (std::size_t i = 0; i < expected.size(); ++i) {
      ASSERT_EQ(mine.recorded[i].single, expected[i].single) << i;
    }
    EXPECT_EQ(mine.lost, ref.stats().lost);
  }
}
