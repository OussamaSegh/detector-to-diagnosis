// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <cmath>

#include "compton.hpp"

namespace {

// The reference: Klein-Nishina shape per unit solid angle (uniform in cos).
double kn(double e, double c) {
  const double p = 1.0 / (1.0 + (e / ex84::electron_rest_energy_kev) * (1.0 - c));
  return p * p * (p + 1.0 / p - (1.0 - c * c));
}

// Integral of kn over [a, b] in cos, by Simpson's rule.
double integral(double e, double a, double b) {
  constexpr int n = 200;
  const double h = (b - a) / n;
  double s = kn(e, a) + kn(e, b);
  for (int i = 1; i < n; ++i) {
    s += (i % 2 == 1 ? 4.0 : 2.0) * kn(e, a + i * h);
  }
  return s * h / 3.0;
}

double chi_square(double e, std::uint64_t seed) {
  constexpr int bins = 40;
  constexpr int samples = 400'000;
  std::array<int, bins> h{};
  std::mt19937_64 rng{seed};
  for (int i = 0; i < samples; ++i) {
    const double c = ex84::sample_cos_theta(e, rng);
    EXPECT_GE(c, -1.0);
    EXPECT_LE(c, 1.0);
    const int b = std::min(bins - 1, static_cast<int>((c + 1.0) / 2.0 * bins));
    ++h[static_cast<std::size_t>(b)];
  }
  const double total = integral(e, -1.0, 1.0);
  double chi2 = 0.0;
  for (int b = 0; b < bins; ++b) {
    const double lo = -1.0 + 2.0 * b / bins;
    const double expected = samples * integral(e, lo, lo + 2.0 / bins) / total;
    const double d = h[static_cast<std::size_t>(b)] - expected;
    chi2 += d * d / expected;
  }
  return chi2;
}

}  // namespace

TEST(Compton, Kinematics) {
  const double e = ex84::electron_rest_energy_kev;
  EXPECT_NEAR(ex84::compton_energy_kev(e, 1.0), e, 1e-9);
  EXPECT_NEAR(ex84::compton_energy_kev(e, 0.0), e / 2.0, 1e-9);
  EXPECT_NEAR(ex84::compton_energy_kev(e, -1.0), e / 3.0, 1e-9);
  EXPECT_LT(ex84::compton_energy_kev(140.0, 0.0), 140.0);
}

TEST(Compton, AngularDistributionAt511) { EXPECT_LT(chi_square(511.0, 1), 80.0); }

TEST(Compton, AngularDistributionAt140) { EXPECT_LT(chi_square(140.0, 2), 80.0); }

TEST(Compton, ForwardFraction) {
  std::mt19937_64 rng{3};
  constexpr int n = 200'000;
  int forward = 0;
  for (int i = 0; i < n; ++i) {
    forward += ex84::sample_cos_theta(511.0, rng) > 0.0 ? 1 : 0;
  }
  const double expected = integral(511.0, 0.0, 1.0) / integral(511.0, -1.0, 1.0);
  EXPECT_NEAR(static_cast<double>(forward) / n, expected, 0.005);
}
