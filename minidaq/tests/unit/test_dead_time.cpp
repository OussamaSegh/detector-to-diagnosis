// SPDX-License-Identifier: MIT
// Dead time and pile-up (Chapter 11): the two models on hand-made streams,
// their agreement with the analytical recorded rates for Poisson input, the
// inverse used for dead-time correction, and the stage's bookkeeping.
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/sim/dead_time.hpp"

using namespace minidaq;
using namespace minidaq::sim;

namespace {

using G = ScannerGeometry;
constexpr std::int64_t ns = 1'000;

// Crystal 0 and crystal 1 are in block 0; crystal 16 is in block 1.
TruthSingle at(std::int64_t t, std::uint32_t transaxial = 0, float kev = 511.0F) {
  return TruthSingle{Single{Picoseconds{t}, G::make_crystal(0, transaxial), KeV{kev}}, 0, 0, false};
}

std::vector<TruthSingle> run(const DeadTimeConfig& c, const std::vector<TruthSingle>& in, DeadTimeStats* st = nullptr) {
  DeadTime d{c};
  std::vector<TruthSingle> out;
  d.push(in, out);
  d.flush(out);
  if (st != nullptr) {
    *st = d.stats();
  }
  return out;
}

std::vector<std::int64_t> times(const std::vector<TruthSingle>& v) {
  std::vector<std::int64_t> t;
  for (const auto& x : v) {
    t.push_back(x.single.time.count());
  }
  return t;
}

// Poisson arrivals at rate n per second on one crystal, for `seconds`.
std::vector<TruthSingle> poisson(double n, double seconds, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::exponential_distribution<double> gap{n * 1e-12};  // per ps
  std::vector<TruthSingle> v;
  double t = 0.0;
  while ((t += gap(rng)) < seconds * 1e12) {
    v.push_back(at(static_cast<std::int64_t>(t)));
  }
  return v;
}

}  // namespace

TEST(DeadTime, NonParalyzableIgnoresArrivalsWhileBusy) {
  // REQ: SRS-DTM-001
  // tau 100 ns: 50 ns is lost and does not extend the dead time, so 120 ns is
  // recorded; 220 ns arrives exactly when the unit is free again.
  const DeadTimeConfig c{DeadTimeModel::non_paralyzable, DeadTimeUnit::block, Picoseconds{100 * ns}, false};
  DeadTimeStats st;
  const auto out = run(c, {at(0), at(50 * ns, 1), at(120 * ns), at(220 * ns)}, &st);
  EXPECT_EQ(times(out), (std::vector<std::int64_t>{0, 120 * ns, 220 * ns}));
  EXPECT_EQ(st.singles_in, 4U);
  EXPECT_EQ(st.recorded, 3U);
  EXPECT_EQ(st.lost, 1U);
}

TEST(DeadTime, ParalyzableExtendsTheDeadTimeWithEveryArrival) {
  // REQ: SRS-DTM-002
  // Each arrival restarts the 100 ns: 50 ns extends to 150, 120 ns to 220, so
  // only 0 and 320 ns are recorded.
  const DeadTimeConfig c{DeadTimeModel::paralyzable, DeadTimeUnit::block, Picoseconds{100 * ns}, false};
  DeadTimeStats st;
  const auto out = run(c, {at(0), at(50 * ns), at(120 * ns), at(320 * ns)}, &st);
  EXPECT_EQ(times(out), (std::vector<std::int64_t>{0, 320 * ns}));
  EXPECT_EQ(st.lost, 2U);
}

TEST(DeadTime, PileUpAddsTheLostEnergy) {
  // REQ: SRS-DTM-003
  const DeadTimeConfig c{DeadTimeModel::non_paralyzable, DeadTimeUnit::block, Picoseconds{100 * ns}, true};
  DeadTimeStats st;
  const auto out = run(c, {at(0, 0, 511.0F), at(30 * ns, 3, 200.0F), at(500 * ns, 0, 300.0F)}, &st);
  ASSERT_EQ(out.size(), 2U);
  EXPECT_FLOAT_EQ(out[0].single.energy.count(), 711.0F) << "now outside a 435 to 585 keV window";
  EXPECT_EQ(out[0].single.crystal, G::make_crystal(0, 0)) << "time and crystal of the first event";
  EXPECT_FLOAT_EQ(out[1].single.energy.count(), 300.0F);
  EXPECT_EQ(st.piled_up, 1U);
}

TEST(DeadTime, UnitsAreIndependent) {
  // REQ: SRS-DTM-004
  // Crystal 16 is in block 1: not affected by block 0's dead time. With one
  // dead time per crystal, crystal 1 is not affected by crystal 0 either.
  const std::vector<TruthSingle> in{at(0, 0), at(10 * ns, 16), at(20 * ns, 1), at(30 * ns, 0)};
  DeadTimeConfig c{DeadTimeModel::non_paralyzable, DeadTimeUnit::block, Picoseconds{100 * ns}, false};
  EXPECT_EQ(times(run(c, in)), (std::vector<std::int64_t>{0, 10 * ns}));
  c.unit = DeadTimeUnit::crystal;
  EXPECT_EQ(times(run(c, in)), (std::vector<std::int64_t>{0, 10 * ns, 20 * ns}));
}

TEST(DeadTime, OutputIsInTimeOrderForAnyChunking) {
  // REQ: SRS-DTM-005
  DetectorSimulator sim{{.activity_bq = 20e6,
                         .source = {SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0},
                         .phantom = {90.0, 180.0},
                         .seed = 4}};
  const auto in = sim.generate_until(Picoseconds{5'000'000'000});  // 5 ms
  for (const auto model : {DeadTimeModel::non_paralyzable, DeadTimeModel::paralyzable}) {
    const DeadTimeConfig c{model, DeadTimeUnit::block, Picoseconds{2'000 * ns}, true};
    DeadTimeStats whole_st;
    const auto whole = run(c, in, &whole_st);
    EXPECT_TRUE(std::is_sorted(whole.begin(), whole.end(),
                               [](const auto& a, const auto& b) { return a.single.time < b.single.time; }));
    EXPECT_EQ(whole_st.singles_in, whole_st.recorded + whole_st.lost);
    EXPECT_EQ(whole.size(), whole_st.recorded);
    EXPECT_GT(whole_st.lost, in.size() / 20) << "the dead time must matter at this rate";
    DeadTime d{c};
    std::vector<TruthSingle> chunked;
    std::mt19937 rng{1};
    for (std::size_t i = 0; i < in.size();) {
      const std::size_t n = std::min<std::size_t>(in.size() - i, rng() % 300);
      d.push(std::span{in}.subspan(i, n), chunked);
      i += n;
    }
    d.flush(chunked);
    ASSERT_EQ(chunked.size(), whole.size());
    for (std::size_t i = 0; i < whole.size(); ++i) {
      ASSERT_EQ(chunked[i].single, whole[i].single) << i;
    }
    EXPECT_EQ(d.stats(), whole_st);
  }
}

TEST(DeadTime, RecordedRatesMatchTheAnalyticalModels) {
  // REQ: SRS-DTM-006
  // n tau = 0.5 on one unit: m = n / 1.5 (non-paralyzable) and n / sqrt(e)
  // (paralyzable). About 300,000 recorded events give a relative standard
  // deviation near 0.2%; the 1% tolerance is about five of them.
  const double n = 5e6;
  const double tau = 100e-9;
  const double seconds = 0.1;
  const auto in = poisson(n, seconds, 7);
  for (const auto model : {DeadTimeModel::non_paralyzable, DeadTimeModel::paralyzable}) {
    DeadTimeStats st;
    (void)run({model, DeadTimeUnit::crystal, Picoseconds{100 * ns}, false}, in, &st);
    const double measured = static_cast<double>(st.recorded) / seconds;
    // Compare with the theory for the rate actually offered, not the nominal one.
    const double offered = static_cast<double>(in.size()) / seconds;
    EXPECT_NEAR(measured / recorded_rate(model, offered, tau), 1.0, 0.01) << to_string(model);
  }
}

TEST(DeadTime, TrueRateInvertsRecordedRate) {
  // REQ: SRS-DTM-007
  const double tau = 200e-9;
  for (const double n : {1e3, 1e5, 1e6, 3e6, 4.9e6}) {
    for (const auto model : {DeadTimeModel::none, DeadTimeModel::non_paralyzable, DeadTimeModel::paralyzable}) {
      EXPECT_NEAR(true_rate(model, recorded_rate(model, n, tau), tau) / n, 1.0, 1e-9) << to_string(model) << " " << n;
    }
  }
  // A paralyzable unit records at most 1 / (e tau), at n = 1 / tau; above it
  // there is no true rate, and above n = 1 / tau the recorded rate falls again.
  const double peak = 1.0 / (std::numbers::e * tau);
  EXPECT_NEAR(recorded_rate(DeadTimeModel::paralyzable, 1.0 / tau, tau), peak, peak * 1e-12);
  EXPECT_NEAR(true_rate(DeadTimeModel::paralyzable, peak, tau) * tau, 1.0, 1e-6);
  EXPECT_TRUE(std::isnan(true_rate(DeadTimeModel::paralyzable, peak * 1.01, tau)));
  EXPECT_LT(recorded_rate(DeadTimeModel::paralyzable, 2.0 / tau, tau), peak);
  EXPECT_TRUE(std::isnan(true_rate(DeadTimeModel::non_paralyzable, 1.0 / tau, tau)));
}

TEST(DeadTime, RejectsBadConfigurations) {
  // REQ: SRS-DTM-008
  EXPECT_FALSE(validate(DeadTimeConfig{DeadTimeModel::paralyzable, DeadTimeUnit::block, Picoseconds{0}, false}));
  EXPECT_FALSE(
      validate(DeadTimeConfig{DeadTimeModel::non_paralyzable, DeadTimeUnit::block, Picoseconds{200'000'000}, false}));
  EXPECT_TRUE(validate(DeadTimeConfig{}));
  EXPECT_THROW(DeadTime(DeadTimeConfig{DeadTimeModel::paralyzable, DeadTimeUnit::block, Picoseconds{-1}, false}),
               std::invalid_argument);
  EXPECT_EQ(parse_dead_time_model("paralyzable").value(), DeadTimeModel::paralyzable);
  EXPECT_FALSE(parse_dead_time_model("paralysable"));
}
