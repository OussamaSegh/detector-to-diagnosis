// SPDX-License-Identifier: MIT
// Exercise 18.3, a solution: tests of the sinogram histogrammer written from sinogram.hpp, one
// behavior each, that take every reachable branch of sinogram.cpp both ways. review.json accepts
// the one branch that no input can take.
#include <gtest/gtest.h>

#include <cstdint>
#include <limits>
#include <string>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/sinogram.hpp"

using namespace minidaq;
using namespace minidaq::sino;

namespace {

Coincidence pair(std::uint32_t ring1, std::uint32_t t1, std::int64_t time1, std::uint32_t ring2, std::uint32_t t2,
                 std::int64_t time2, CoincidenceKind kind = CoincidenceKind::prompt) {
  return Coincidence{Single{Picoseconds{time1}, ScannerGeometry::make_crystal(ring1, t1), KeV{511.0F}},
                     Single{Picoseconds{time2}, ScannerGeometry::make_crystal(ring2, t2), KeV{511.0F}}, kind};
}

// Crystals 10 and 200 of a ring: a LOR 2 radial bins from the center, with crystal 10 as
// endpoint a (no wrap). Crystals 0 and 10 and 0 and 350 are far outside the default FOV, on
// either side.
constexpr std::uint32_t near_a = 10;
constexpr std::uint32_t near_b = 200;

std::string why(const SinogramConfig& c) {
  const auto v = validate(c);
  return v ? "valid" : v.error();
}

}  // namespace

// [snippet:validate]
TEST(SinogramBranches, TheConfigurationIsCheckedRuleByRule) {
  EXPECT_EQ(why(SinogramConfig{}), "valid");
  SinogramConfig c;
  c.fov_radius_mm = 0.0;
  EXPECT_NE(why(c), "valid") << "the FOV radius must be positive";
  c.fov_radius_mm = ScannerGeometry::inner_radius_mm;
  EXPECT_NE(why(c), "valid") << "and inside the ring";
  c.fov_radius_mm = std::numeric_limits<double>::quiet_NaN();
  EXPECT_NE(why(c), "valid") << "and a number";
  c = {};
  c.max_ring_difference = num_rings;
  EXPECT_NE(why(c), "valid");
  c.max_ring_difference = num_rings - 1;
  EXPECT_EQ(why(c), "valid") << "47 keeps every ring pair";
  c = {};
  c.tof_bins = 0;
  EXPECT_NE(why(c), "valid");
  c.tof_bins = 256;
  EXPECT_NE(why(c), "valid");
  c.tof_bins = 2;
  EXPECT_NE(why(c), "valid") << "TOF needs a bin width";
  c.tof_bin_ps = 1;
  EXPECT_EQ(why(c), "valid");
  c = {};
  c.delayed_window_ps = -1;
  EXPECT_NE(why(c), "valid");
}
// [/snippet:validate]

TEST(SinogramBranches, ACrystalOutsideTheScannerIsRejectedOnEitherSide) {
  const Histogrammer h{SinogramConfig{}};
  const CrystalId bad{ScannerGeometry::num_crystals};
  auto c = pair(0, near_a, 0, 0, near_b, 100);
  c.first.crystal = bad;
  EXPECT_EQ(h.locate(c).outcome, Outcome::invalid_crystal);
  c = pair(0, near_a, 0, 0, near_b, 100);
  c.second.crystal = bad;
  EXPECT_EQ(h.locate(c).outcome, Outcome::invalid_crystal);
}

TEST(SinogramBranches, TwoCrystalsAtOneTransaxialPositionHaveNoAngle) {
  const Histogrammer h{SinogramConfig{}};
  EXPECT_EQ(h.locate(pair(0, near_a, 0, 5, near_a, 100)).outcome, Outcome::no_angle);
}

TEST(SinogramBranches, LorsOutsideTheFieldOfViewAreRejectedOnBothSides) {
  const Histogrammer h{SinogramConfig{}};
  const auto low = h.locate(pair(0, 0, 0, 0, 10, 100));
  EXPECT_EQ(low.outcome, Outcome::outside_fov);
  EXPECT_LT(low.radial, -h.max_radial());
  const auto high = h.locate(pair(0, 0, 0, 0, 350, 100));
  EXPECT_EQ(high.outcome, Outcome::outside_fov);
  EXPECT_GT(high.radial, h.max_radial());
}

TEST(SinogramBranches, TheRingDifferenceCutAppliesInBothDirections) {
  SinogramConfig c;
  c.max_ring_difference = 3;
  const Histogrammer h{c};
  EXPECT_EQ(h.locate(pair(0, near_a, 0, 4, near_b, 100)).outcome, Outcome::ring_difference);
  EXPECT_EQ(h.locate(pair(4, near_a, 0, 0, near_b, 100)).outcome, Outcome::ring_difference);
  EXPECT_EQ(h.locate(pair(0, near_a, 0, 3, near_b, 100)).outcome, Outcome::binned);
}

// [snippet:tof]
TEST(SinogramBranches, TauBeyondTheOuterTofBinsIsRejectedOnBothSides) {
  SinogramConfig c;
  c.tof_bins = 3;
  c.tof_bin_ps = 1000;  // bins of tau: [-1500, -500), [-500, 500), [500, 1500)
  const Histogrammer h{c};
  // Crystal 10 is endpoint a, so tau = t_a - t_b.
  EXPECT_EQ(h.locate(pair(0, near_a, 0, 0, near_b, 1500)).outcome, Outcome::binned);  // tau -1500: bin 0
  EXPECT_EQ(h.locate(pair(0, near_a, 0, 0, near_b, 1501)).outcome, Outcome::tof_outside);
  const auto last = h.locate(pair(0, near_b, 0, 0, near_a, 1499));  // a hit 1499 ps later: tau 1499
  EXPECT_EQ(last.outcome, Outcome::binned);
  EXPECT_EQ(last.tof, 2U);
  EXPECT_EQ(h.locate(pair(0, near_b, 0, 0, near_a, 1500)).outcome, Outcome::tof_outside);
}
// [/snippet:tof]

TEST(SinogramBranches, EachOutcomeHasItsOwnCounter) {
  SinogramConfig c;
  c.max_ring_difference = 3;
  c.tof_bins = 3;
  c.tof_bin_ps = 1000;
  Histogrammer h{c};
  auto bad = pair(0, near_a, 0, 0, near_b, 100);
  bad.first.crystal = CrystalId{ScannerGeometry::num_crystals};
  h.add(bad);
  h.add(pair(0, near_a, 0, 5, near_a, 100));
  h.add(pair(0, 0, 0, 0, 10, 100));
  h.add(pair(0, near_a, 0, 4, near_b, 100));
  h.add(pair(0, near_a, 0, 0, near_b, 2000));
  h.add(pair(0, near_a, 0, 0, near_b, 100));
  const auto& s = h.stats();
  EXPECT_EQ(s.invalid_crystal, 1U);
  EXPECT_EQ(s.no_angle, 1U);
  EXPECT_EQ(s.outside_fov, 1U);
  EXPECT_EQ(s.ring_difference, 1U);
  EXPECT_EQ(s.tof_outside, 1U);
  EXPECT_EQ(s.prompts, 1U);
  EXPECT_EQ(s.delayeds, 0U);
}

TEST(SinogramBranches, TheMichelogramCountsPromptsBeforeTheCutAndNoDelayeds) {
  SinogramConfig c;
  c.max_ring_difference = 3;
  Histogrammer h{c};
  h.add(pair(0, near_a, 0, 4, near_b, 100));                                         // cut
  h.add(pair(1, near_a, 0, 2, near_b, 100'100, CoincidenceKind::delayed));            // delayed
  h.add(pair(0, 0, 0, 0, 10, 100));                                                  // outside the FOV
  EXPECT_EQ(h.michelogram()[0 * num_rings + 4], 1U);
  EXPECT_EQ(h.michelogram()[1 * num_rings + 2], 0U);
  std::uint64_t total = 0;
  for (const auto n : h.michelogram()) {
    total += n;
  }
  EXPECT_EQ(total, 1U);
  EXPECT_EQ(h.stats().delayeds, 1U);
}

TEST(SinogramBranches, PromptsAndDelayedsCollapseApart) {
  Histogrammer h{SinogramConfig{}};
  h.add(pair(0, near_a, 0, 0, near_b, 100));
  h.add(pair(2, near_a, 0, 0, near_b, 100));
  h.add(pair(0, near_a, 0, 0, near_b, 100'100, CoincidenceKind::delayed));
  const auto b = *lor_bin(near_a, near_b);
  const auto at = std::size_t{b.view} * h.radial_bins() + static_cast<std::size_t>(b.radial + h.max_radial());
  EXPECT_EQ(h.collapsed(false)[at], 2U);
  EXPECT_EQ(h.collapsed(true)[at], 1U);
}

TEST(SinogramBranches, TheHeaderDescribesTheData) {
  Histogrammer h{SinogramConfig{}};
  h.add(pair(0, near_a, 0, 0, near_b, 100));
  const auto text = interfile_header(h, "p.bin", "d.bin", "test");
  EXPECT_NE(text.find("prompts data file := p.bin"), std::string::npos);
  EXPECT_NE(text.find("prompts binned := 1"), std::string::npos);
  EXPECT_NE(text.find("matrix size [radial] := " + std::to_string(h.radial_bins())), std::string::npos);
}
