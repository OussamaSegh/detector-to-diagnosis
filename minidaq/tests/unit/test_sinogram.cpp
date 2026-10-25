// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <numbers>
#include <random>
#include <set>
#include <utility>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/sinogram.hpp"
#include "minidaq/sim/detector_simulator.hpp"

using namespace minidaq;
using namespace minidaq::sino;

namespace {

constexpr double pi = std::numbers::pi;
constexpr auto n_ring = static_cast<double>(crystals_per_ring);

Coincidence pair(std::uint32_t ring1, std::uint32_t t1, std::int64_t time1, std::uint32_t ring2, std::uint32_t t2,
                 std::int64_t time2, CoincidenceKind kind = CoincidenceKind::prompt) {
  Single a{Picoseconds{time1}, ScannerGeometry::make_crystal(ring1, t1), KeV{511.0F}};
  Single b{Picoseconds{time2}, ScannerGeometry::make_crystal(ring2, t2), KeV{511.0F}};
  if (b.time < a.time) {
    std::swap(a, b);  // first is the earlier single, as the sorter emits it
  }
  return Coincidence{a, b, kind};
}

// The normal angle of the LOR (i, j) in [0, pi), and its signed distance
// along that normal, computed from the crystal positions.
std::pair<double, double> normal_and_distance(std::uint32_t i, std::uint32_t j) {
  const double theta = static_cast<double>((i + j + 1) % crystals_per_ring) * pi / n_ring;
  const auto p = crystal_xy_table[i];
  return {theta, p.x * std::cos(theta) + p.y * std::sin(theta)};
}

}  // namespace

TEST(Sinogram, EveryTransaxialLorHasItsOwnBin) {
  // REQ: SRS-SNO-001
  std::set<std::pair<std::uint32_t, std::int32_t>> seen;
  for (std::uint32_t i = 0; i < crystals_per_ring; ++i) {
    EXPECT_FALSE(lor_bin(i, i));
    for (std::uint32_t j = i + 1; j < crystals_per_ring; ++j) {
      const auto b = lor_bin(i, j);
      ASSERT_TRUE(b);
      EXPECT_EQ(lor_bin(j, i)->view, b->view);
      EXPECT_LT(b->view, num_views);
      EXPECT_LE(std::abs(b->radial), 191);
      EXPECT_TRUE(seen.insert({b->view, b->radial}).second) << i << " " << j;
    }
  }
  // 384 * 383 / 2 = 73,536 LORs fill 192 views of 383 radial bins exactly.
  EXPECT_EQ(seen.size(), 192U * 383U);
}

TEST(Sinogram, RadialPositionIsTheDistanceOfTheLorFromTheAxis) {
  // REQ: SRS-SNO-001
  for (std::uint32_t i = 0; i < crystals_per_ring; i += 5) {
    for (std::uint32_t j = i + 1; j < crystals_per_ring; j += 3) {
      const auto b = lor_bin(i, j);
      const auto [theta, s] = normal_and_distance(i, j);
      EXPECT_NEAR(radial_position_mm(b->radial), s, 1e-9) << i << " " << j;
      const auto q = crystal_xy_table[j];  // the other end is on the same line
      EXPECT_NEAR(q.x * std::cos(theta) + q.y * std::sin(theta), s, 1e-9);
      // View v holds the angles 2v and 2v + 1 (in units of pi / N).
      EXPECT_EQ(b->view, static_cast<std::uint32_t>(std::lround(theta * n_ring / pi)) / 2);
    }
  }
  EXPECT_EQ(max_radial_bin(120.0), 113);  // 150 sin(113 pi / 384) = 119.7 mm; r = 114 is at 120.5 mm
  EXPECT_LT(std::abs(radial_position_mm(113)), 120.0);
  EXPECT_GT(std::abs(radial_position_mm(114)), 120.0);
}

TEST(Sinogram, AgreesWithTheSortersFieldOfViewCut) {
  // REQ: SRS-SNO-002
  SorterConfig sc;
  sc.fov_radius_mm = 120.0;
  sc.min_sector_difference = 0;
  const CoincidenceSorter sorter{sc};
  const Histogrammer h{SinogramConfig{}};
  for (std::uint32_t i = 0; i < crystals_per_ring; ++i) {
    for (std::uint32_t j = i + 1; j < crystals_per_ring; ++j) {
      const Single a{Picoseconds{0}, CrystalId{i}, KeV{511.0F}};
      const Single b{Picoseconds{0}, CrystalId{j}, KeV{511.0F}};
      ASSERT_EQ(sorter.good(a, b), std::abs(lor_bin(i, j)->radial) <= h.max_radial()) << i << " " << j;
    }
  }
}

TEST(Sinogram, RingPairsGoToTheirSsrbSliceAndTheMichelogram) {
  // REQ: SRS-SNO-003
  SinogramConfig c;
  c.max_ring_difference = 5;
  Histogrammer h{c};
  h.add(pair(3, 10, 0, 7, 200, 100));     // difference 4: slice 10
  h.add(pair(30, 10, 0, 40, 200, 100));   // difference 10: cut
  h.add(pair(7, 200, 0, 3, 10, 100));     // the same LOR, other way round: slice 10
  EXPECT_EQ(h.stats().prompts, 2U);
  EXPECT_EQ(h.stats().ring_difference, 1U);
  const auto b = *lor_bin(10, 200);
  EXPECT_EQ(h.prompts()[h.index(0, 10, b.view, b.radial)], 2U);
  // Endpoint a of this bin is crystal 10 if a_is_lower, so its ring is 3.
  const auto ra = b.a_is_lower ? 3U : 7U;
  const auto rb = b.a_is_lower ? 7U : 3U;
  EXPECT_EQ(h.michelogram()[ra * num_rings + rb], 2U);
  EXPECT_EQ(h.michelogram()[(b.a_is_lower ? 30U : 40U) * num_rings + (b.a_is_lower ? 40U : 30U)], 1U)
      << "the Michelogram counts before the ring-difference cut";
}

TEST(Sinogram, TimeOfFlightBinsLocateTheAnnihilationAlongTheLor) {
  // REQ: SRS-SNO-004
  SinogramConfig c;
  c.tof_bins = 41;
  c.tof_bin_ps = 50;  // 7.5 mm of position per bin
  const double c_mm = speed_of_light_mm_per_ps;
  std::mt19937_64 rng{21};
  std::uniform_int_distribution<std::uint32_t> crystal(0, crystals_per_ring - 1);
  std::uniform_real_distribution<double> along(0.2, 0.8);
  const Histogrammer h{c};
  int checked = 0;
  for (int trial = 0; trial < 3000; ++trial) {
    const auto i = crystal(rng);
    const auto j = crystal(rng);
    const auto b = lor_bin(i, j);
    if (!b || std::abs(b->radial) > max_radial_bin(c.fov_radius_mm)) {
      continue;
    }
    // An annihilation at fraction f from crystal i to crystal j.
    const auto pi_ = crystal_xy_table[i];
    const auto pj = crystal_xy_table[j];
    const double f = along(rng);
    const double x = pi_.x + f * (pj.x - pi_.x);
    const double y = pi_.y + f * (pj.y - pi_.y);
    const double len = std::hypot(pj.x - pi_.x, pj.y - pi_.y);
    const auto ti = std::llround(std::hypot(x - pi_.x, y - pi_.y) / c_mm);
    const auto tj = std::llround(std::hypot(x - pj.x, y - pj.y) / c_mm);
    const auto p = h.locate(pair(0, i, 1'000'000 + ti, 0, j, 1'000'000 + tj));
    ASSERT_EQ(p.outcome, Outcome::binned);
    EXPECT_EQ(p.view, b->view);
    const auto hit = p.tof;
    ASSERT_LT(hit, c.tof_bins);
    // The bin's center, as a distance from the midpoint towards endpoint b.
    const double tau_center = (static_cast<double>(hit) - (c.tof_bins - 1) / 2.0) * static_cast<double>(c.tof_bin_ps);
    const double toward_b = c_mm * tau_center / 2.0;
    // Endpoint b is crystal j if a is the lower index and i < j, and so on.
    const bool b_is_j = (i < j) == b->a_is_lower;
    const double true_toward_b = (b_is_j ? f - 0.5 : 0.5 - f) * len;
    EXPECT_NEAR(toward_b, true_toward_b, c_mm * static_cast<double>(c.tof_bin_ps) / 4.0 + 0.2)
        << "LOR " << i << "-" << j << " f " << f;
    ++checked;
  }
  EXPECT_GT(checked, 1000);
}

TEST(Sinogram, DelayedPairsAreBinnedApartWithTheDelayRemoved) {
  // REQ: SRS-SNO-004
  SinogramConfig c;
  c.tof_bins = 3;
  c.tof_bin_ps = 1000;
  Histogrammer h{c};
  // Crystal 10 is the earlier single in all three; the delay is 100 ns.
  h.add(pair(0, 10, 0, 0, 200, 100'000 + 100, CoincidenceKind::delayed));   // |tau| = 100: middle bin
  h.add(pair(0, 10, 0, 0, 200, 100'000 + 1100, CoincidenceKind::delayed));  // |tau| = 1100: an outer bin
  h.add(pair(0, 10, 0, 0, 200, 100'000 + 1600, CoincidenceKind::delayed));  // beyond the outer bin's 1500
  EXPECT_EQ(h.stats().delayeds, 2U);
  EXPECT_EQ(h.stats().prompts, 0U);
  EXPECT_EQ(h.stats().tof_outside, 1U);
  const auto b = *lor_bin(10, 200);
  EXPECT_EQ(h.delayeds()[h.index(1, 0, b.view, b.radial)], 1U);
  // If crystal 10 is endpoint a, it was hit first: tau = t_a - t_b < 0, bin 0.
  EXPECT_EQ(h.delayeds()[h.index(b.a_is_lower ? 0 : 2, 0, b.view, b.radial)], 1U);
  EXPECT_EQ(h.collapsed(true)[std::size_t{b.view} * h.radial_bins() + static_cast<std::size_t>(b.radial + h.max_radial())],
            2U);
}

TEST(Sinogram, APointSourceDrawsASinusoid) {
  // REQ: SRS-SNO-005
  sim::SimulatorConfig sc;
  sc.activity_bq = 2e5;
  sc.source.centre_mm = {40.0, -25.0, 0.0};
  sc.non_collinearity_fwhm_deg = 0.0;
  sim::DetectorSimulator sim{sc};
  SorterConfig so;
  so.fov_radius_mm = 120.0;
  so.delay = Picoseconds{0};
  CoincidenceSorter sorter{so};
  Histogrammer h{SinogramConfig{}};
  std::vector<sim::TruthSingle> truth(4096);
  std::vector<Single> singles(truth.size());
  std::vector<Coincidence> out;
  for (int chunk = 0; chunk < 100; ++chunk) {
    sim.generate(truth);
    for (std::size_t k = 0; k < truth.size(); ++k) {
      singles[k] = truth[k].single;
    }
    out.clear();
    sorter.push(singles, out);
    h.add(out);
  }
  ASSERT_GT(h.stats().prompts, 20'000U);
  // In every view, the counts sit where the LORs through the source are:
  // s = x0 cos(theta) + y0 sin(theta).
  const auto plane = h.collapsed();
  double worst = 0.0;
  double sum_err = 0.0;
  for (std::uint32_t v = 0; v < num_views; ++v) {
    const double theta = (2.0 * v + 0.5) * pi / n_ring;
    const double expected = 40.0 * std::cos(theta) - 25.0 * std::sin(theta);
    double sum = 0.0;
    double sum_s = 0.0;
    for (std::int32_t r = -h.max_radial(); r <= h.max_radial(); ++r) {
      const auto n = static_cast<double>(plane[std::size_t{v} * h.radial_bins() + static_cast<std::size_t>(r + h.max_radial())]);
      sum += n;
      sum_s += n * radial_position_mm(r);
    }
    ASSERT_GT(sum, 0.0) << "view " << v;
    const double err = std::abs(sum_s / sum - expected);
    worst = std::max(worst, err);
    sum_err += err;
  }
  std::printf("point source sinusoid: mean |error| %.3f mm, worst %.3f mm\n", sum_err / num_views, worst);
  EXPECT_LT(worst, 3.0);
}
