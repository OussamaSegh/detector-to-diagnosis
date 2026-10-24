#include <gtest/gtest.h>

#include <cmath>
#include <numbers>

#include "ring_table.hpp"

// The starter compiles too: these only check that the table is a constant.
constexpr double kFirstX = ex::ring384[0].x;
static_assert(ex::ring384.size() == 384);

TEST(ConstexprLut, PointsOnCircle) {
  for (const auto& p : ex::ring384) {
    EXPECT_NEAR(std::hypot(p.x, p.y), 150.0, 1e-9);
  }
}

TEST(ConstexprLut, Spacing) {
  const double expected = 2.0 * std::numbers::pi * 150.0 / 384.0;
  for (std::size_t i = 0; i + 1 < ex::ring384.size(); ++i) {
    const auto& a = ex::ring384[i];
    const auto& b = ex::ring384[i + 1];
    EXPECT_NEAR(std::hypot(a.x - b.x, a.y - b.y), expected, 1e-3);
  }
}

TEST(ConstexprLut, FirstCrystalInFirstQuadrant) {
  EXPECT_GT(kFirstX, 0.0);
  EXPECT_GT(ex::ring384[0].y, 0.0);
}
