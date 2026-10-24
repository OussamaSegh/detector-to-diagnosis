// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>

#include "minidaq/core/constexpr_math.hpp"
#include "minidaq/core/geometry.hpp"

using namespace minidaq;
using G = ScannerGeometry;

static_assert(G::num_crystals == 18432);
static_assert(G::num_crystals < (1U << 15), "crystal id must fit the 15-bit packed field");
static_assert(G::block_of(G::make_crystal(0, 0)) == 0);
static_assert(G::block_of(G::make_crystal(47, 383)) == G::num_blocks - 1);

TEST(ConstexprMath, MatchesStdLib) {
  for (int i = -2000; i <= 2000; ++i) {
    const double x = i * 0.0137;
    EXPECT_NEAR(cmath::sin(x), std::sin(x), 1e-13) << x;
    EXPECT_NEAR(cmath::cos(x), std::cos(x), 1e-13) << x;
  }
}

TEST(Geometry, CrystalsLieOnTheRing) {
  for (const auto& p : crystal_xy_table) {
    EXPECT_NEAR(std::hypot(p.x, p.y), G::inner_radius_mm, 1e-9);
  }
  // Neighbouring crystals are one transaxial pitch apart (chord ~ arc here).
  const auto& a = crystal_xy_table[0];
  const auto& b = crystal_xy_table[1];
  EXPECT_NEAR(std::hypot(a.x - b.x, a.y - b.y), G::transaxial_pitch_mm, 1e-3);
}

TEST(Geometry, AxialPositionsAreCentred) {
  EXPECT_NEAR(crystal_z_mm(0), -crystal_z_mm(G::crystal_rings - 1), 1e-12);
}

TEST(Geometry, IdDecomposition) {
  const CrystalId c = G::make_crystal(17, 100);
  EXPECT_EQ(G::ring_of(c), 17U);
  EXPECT_EQ(G::transaxial_of(c), 100U);
  EXPECT_EQ(G::block_of(c), 1U * G::blocks_per_ring + 100U / 16U);
  EXPECT_FALSE(G::valid(CrystalId{G::num_crystals}));
}
