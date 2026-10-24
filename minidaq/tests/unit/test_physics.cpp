// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <numbers>

#include "minidaq/sim/physics.hpp"

namespace ph = minidaq::sim::physics;

TEST(Physics, ComptonKinematics) {
  // REQ: SRS-SIM-010
  EXPECT_DOUBLE_EQ(ph::compton_energy_kev(511.0, 1.0), 511.0);  // no deflection, no loss
  // Backscatter of an annihilation photon: E' = E / 3 exactly, since E = m_e c^2.
  EXPECT_NEAR(ph::compton_energy_kev(ph::annihilation_energy_kev, -1.0), ph::annihilation_energy_kev / 3.0, 1e-9);
  // 90 degrees: E' = E / 2 for E = m_e c^2.
  EXPECT_NEAR(ph::compton_energy_kev(ph::annihilation_energy_kev, 0.0), ph::annihilation_energy_kev / 2.0, 1e-9);
}

TEST(Physics, KleinNishinaShapeIsBoundedByTwo) {
  for (double e : {50.0, 140.0, 511.0, 1000.0}) {
    EXPECT_NEAR(ph::klein_nishina_shape(e, 1.0), 2.0, 1e-12);
    for (int i = 0; i <= 200; ++i) {
      const double c = -1.0 + 0.01 * i;
      EXPECT_LE(ph::klein_nishina_shape(e, c), 2.0 + 1e-12);
      EXPECT_GT(ph::klein_nishina_shape(e, c), 0.0);
    }
  }
  // At 511 keV forward scattering dominates: backward is far less likely.
  EXPECT_LT(ph::klein_nishina_shape(511.0, -1.0), 0.25 * ph::klein_nishina_shape(511.0, 1.0));
}

TEST(Physics, WaterAttenuation) {
  // REQ: SRS-SIM-011
  EXPECT_NEAR(ph::water_mu_per_mm(511.0), 0.0096, 0.0001);  // about 0.096 per cm at 511 keV
  EXPECT_NEAR(ph::water_mu_per_mm(100.0), 0.01707, 1e-6);
  EXPECT_GT(ph::water_mu_per_mm(200.0), ph::water_mu_per_mm(400.0));  // lower energy, more attenuation
  EXPECT_DOUBLE_EQ(ph::water_mu_per_mm(20.0), ph::water_mu_per_mm(100.0));  // clamped to the table
}

TEST(Physics, CylinderExit) {
  const ph::Vec3 centre{0, 0, 0};
  EXPECT_NEAR(*ph::exit_distance_cylinder(centre, {1, 0, 0}, 150.0), 150.0, 1e-9);
  // At 45 degrees to the axis the path to the side is r / sin(theta).
  const double s = std::numbers::sqrt2 / 2.0;
  EXPECT_NEAR(*ph::exit_distance_cylinder(centre, {s, 0, s}, 150.0), 150.0 / s, 1e-9);
  EXPECT_FALSE(ph::exit_distance_cylinder(centre, {0, 0, 1}, 150.0).has_value());
  // From an off-centre point, back across the centre.
  EXPECT_NEAR(*ph::exit_distance_cylinder({100, 0, 0}, {-1, 0, 0}, 150.0), 250.0, 1e-9);
  EXPECT_NEAR(ph::exit_distance_slab({0, 0, 10}, {0, 0, -1}, 50.0), 60.0, 1e-9);
}

TEST(Physics, RotateKeepsUnitLengthAndAngle) {
  const ph::Vec3 d{0.6, 0.0, 0.8};
  for (double c : {1.0, 0.5, 0.0, -0.7, -1.0}) {
    for (double phi : {0.0, 1.0, 3.0, 5.5}) {
      const ph::Vec3 r = ph::rotate(d, c, phi);
      EXPECT_NEAR(ph::norm(r), 1.0, 1e-12);
      EXPECT_NEAR(ph::dot(r, d), c, 1e-12);
    }
  }
}
