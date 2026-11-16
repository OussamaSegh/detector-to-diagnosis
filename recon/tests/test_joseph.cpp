// SPDX-License-Identifier: MIT
// Tests of the C++ projector (Chapter 29). The geometry is a small parallel-beam one, so that
// each test can say what the right answer is; tools/test_recon_cpp.py runs the Python tests of
// the numpy projector on this one with MiniDAQ's geometry.
#include "recon/joseph.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <numbers>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>

namespace {

struct Geometry {
  std::size_t views = 60, bins = 81, n = 64;
  double pixel_mm = 2.0;
  std::vector<double> s, phi;
  Geometry() : s(views * bins), phi(views * bins) {
    for (std::size_t v = 0; v < views; ++v) {
      for (std::size_t b = 0; b < bins; ++b) {
        s[(v * bins) + b] = (static_cast<double>(b) - 40.0) * 1.6;  // bins of 1.6 mm
        phi[(v * bins) + b] = static_cast<double>(v) * std::numbers::pi / 60.0;
      }
    }
  }
  recon::JosephProjector projector() const {
    return {s, phi, views, bins, n, pixel_mm};
  }
  // 21 TOF bins of 100 ps (15 mm along the line): +-157 mm, the whole image and 3 sigma more.
  static constexpr std::size_t tof_bins = 21;
  recon::JosephProjector tof_projector() const {
    return {s, phi, views, bins, n, pixel_mm, recon::Tof{tof_bins, 100.0, 300.0}};
  }
  std::vector<std::size_t> all() const {
    std::vector<std::size_t> v(views);
    std::iota(v.begin(), v.end(), 0U);
    return v;
  }
  double x(std::size_t col) const { return (static_cast<double>(col) - 31.5) * pixel_mm; }
};

std::vector<double> random_vector(std::size_t size, unsigned seed) {
  std::mt19937_64 rng(seed);
  std::uniform_real_distribution<double> u(0.0, 1.0);
  std::vector<double> v(size);
  for (auto& e : v) e = u(rng);
  return v;
}

double dot(const std::vector<double>& a, const std::vector<double>& b) {
  return std::inner_product(a.begin(), a.end(), b.begin(), 0.0);
}

TEST(JosephProjector, BackIsTheAdjointOfForward) {
  // REQ: SRS-REC-001
  const Geometry g;
  const auto p = g.projector();
  for (unsigned seed = 1; seed <= 5; ++seed) {
    const auto x = random_vector(g.n * g.n, seed);
    const auto y = random_vector(g.views * g.bins, seed + 100);
    std::vector<double> ax(g.views * g.bins);
    std::vector<double> aty(g.n * g.n);
    p.forward(x, g.all(), ax);
    p.back(y, g.all(), aty);
    EXPECT_NEAR(dot(ax, y) / dot(x, aty), 1.0, 1e-12);
  }
}

TEST(JosephProjector, ADiscProjectsToItsChords) {
  // REQ: SRS-REC-001
  const Geometry g;
  const auto p = g.projector();
  std::vector<double> disc(g.n * g.n);
  for (std::size_t r = 0; r < g.n; ++r) {
    for (std::size_t c = 0; c < g.n; ++c) {
      disc[(r * g.n) + c] = (g.x(c) * g.x(c)) + (g.x(r) * g.x(r)) <= 40.0 * 40.0 ? 1.0 : 0.0;
    }
  }
  std::vector<double> got(g.views * g.bins);
  p.forward(disc, g.all(), got);
  double worst = 0.0;
  for (std::size_t i = 0; i < got.size(); ++i) {
    const double s = g.s[i];
    if (std::abs(s) < 35.0) {
      worst = std::max(worst, std::abs(got[i] - (2.0 * std::sqrt((40.0 * 40.0) - (s * s)))));
    }
  }
  EXPECT_LT(worst, 4.0);  // a disc of square pixels has a ragged edge
}

TEST(JosephProjector, AnOffCenterPointLiesOnItsSinusoid) {
  // REQ: SRS-REC-001
  const Geometry g;
  const auto p = g.projector();
  std::vector<double> point(g.n * g.n, 0.0);
  const std::size_t row = 20;  // y = -23
  const std::size_t col = 45;  // x = 27
  point[(row * g.n) + col] = 1.0;
  std::vector<double> got(g.views * g.bins);
  p.forward(point, g.all(), got);
  for (std::size_t v = 0; v < g.views; ++v) {
    const auto first = got.begin() + static_cast<std::ptrdiff_t>(v * g.bins);
    const auto peak = static_cast<std::size_t>(
        std::max_element(first, first + static_cast<std::ptrdiff_t>(g.bins)) - first);
    const double phi = g.phi[v * g.bins];
    const double want = (g.x(col) * std::cos(phi)) + (g.x(row) * std::sin(phi));
    EXPECT_NEAR(g.s[(v * g.bins) + peak], want, 1.6) << "view " << v;
  }
}

TEST(JosephProjector, TheThreadsDoNotChangeTheResult) {
  // REQ: SRS-REC-006
  const Geometry g;
  const auto p = g.projector();
  const auto x = random_vector(g.n * g.n, 7);
  const auto y = random_vector(g.views * g.bins, 8);
  std::vector<double> f1(g.views * g.bins), f4(g.views * g.bins), b1(g.n * g.n), b4(g.n * g.n);
  p.forward(x, g.all(), f1, 1);
  p.forward(x, g.all(), f4, 4);
  EXPECT_EQ(f1, f4);  // one thread per line: bit for bit
  p.back(y, g.all(), b1, 1);
  p.back(y, g.all(), b4, 4);
  for (std::size_t i = 0; i < b1.size(); ++i) {
    ASSERT_NEAR(b4[i], b1[i], 1e-12 * std::max(1.0, std::abs(b1[i]))) << "pixel " << i;
  }
  std::vector<double> again(g.n * g.n);
  p.back(y, g.all(), again, 4);
  EXPECT_EQ(again, b4);  // the same thread count: bit for bit
}

TEST(JosephProjector, ASubsetIsTheRowsOfItsViews) {
  // REQ: SRS-REC-003
  const Geometry g;
  const auto p = g.projector();
  const auto x = random_vector(g.n * g.n, 9);
  std::vector<double> full(g.views * g.bins);
  p.forward(x, g.all(), full);
  const std::vector<std::size_t> subset{3, 13, 23, 33, 43, 53};
  std::vector<double> part(subset.size() * g.bins);
  p.forward(x, subset, part);
  for (std::size_t k = 0; k < subset.size(); ++k) {
    for (std::size_t b = 0; b < g.bins; ++b) {
      EXPECT_EQ(part[(k * g.bins) + b], full[(subset[k] * g.bins) + b]);
    }
  }
}

TEST(JosephProjector, RefusesWhatDoesNotFit) {
  // REQ: SRS-REC-005
  const Geometry g;
  EXPECT_THROW(recon::JosephProjector(g.s, g.phi, g.views, g.bins + 1, g.n, 2.0),
               std::invalid_argument);
  EXPECT_THROW(recon::JosephProjector(g.s, g.phi, g.views, g.bins, 0, 2.0), std::invalid_argument);
  EXPECT_THROW(recon::JosephProjector(g.s, g.phi, g.views, g.bins, g.n, 0.0),
               std::invalid_argument);
  auto bad = g.phi;
  bad[5] = std::nan("");
  EXPECT_THROW(recon::JosephProjector(g.s, bad, g.views, g.bins, g.n, 2.0), std::invalid_argument);
  const auto p = g.projector();
  std::vector<double> image(g.n * g.n), out(g.bins);
  EXPECT_THROW(p.forward(image, std::vector<std::size_t>{60}, out), std::out_of_range);
  std::vector<double> small(g.n * g.n - 1);
  EXPECT_THROW(p.forward(small, std::vector<std::size_t>{0}, out), std::invalid_argument);
  EXPECT_THROW(p.back(out, std::vector<std::size_t>{0, 1}, image), std::invalid_argument);
}

// Time of flight (Chapter 39).

TEST(TofProjector, BackIsTheAdjointOfForward) {
  // REQ: SRS-REC-007
  const Geometry g;
  const auto p = g.tof_projector();
  const std::size_t size = g.views * g.bins * Geometry::tof_bins;
  for (unsigned seed = 1; seed <= 3; ++seed) {
    const auto x = random_vector(g.n * g.n, seed);
    const auto y = random_vector(size, seed + 100);
    std::vector<double> ax(size);
    std::vector<double> aty(g.n * g.n);
    p.forward(x, g.all(), ax);
    p.back(y, g.all(), aty);
    EXPECT_NEAR(dot(ax, y) / dot(x, aty), 1.0, 1e-12);
  }
}

TEST(TofProjector, TheTofBinsAddUpToTheProjectionWithoutTof) {
  // REQ: SRS-REC-007
  const Geometry g;
  // An object within 60 mm of the axis, 5 standard deviations inside the outer bins' edges.
  auto x = random_vector(g.n * g.n, 21);
  for (std::size_t r = 0; r < g.n; ++r) {
    for (std::size_t c = 0; c < g.n; ++c) {
      if (std::hypot(g.x(c), g.x(r)) >= 60.0) {
        x[(r * g.n) + c] = 0.0;
      }
    }
  }
  std::vector<double> plain(g.views * g.bins);
  std::vector<double> tof(g.views * g.bins * Geometry::tof_bins);
  g.projector().forward(x, g.all(), plain);
  g.tof_projector().forward(x, g.all(), tof);
  for (std::size_t l = 0; l < plain.size(); ++l) {
    double sum = 0.0;
    for (std::size_t j = 0; j < Geometry::tof_bins; ++j) {
      sum += tof[(l * Geometry::tof_bins) + j];
    }
    ASSERT_NEAR(sum, plain[l], 1e-6 * std::max(1.0, plain[l])) << "line " << l;
  }
}

TEST(TofProjector, APointLiesWhereItsTimeOfFlightSays) {
  // REQ: SRS-REC-007
  // Along the line through the point, the TOF profile's mean is the point's own position on the
  // line, p . (-sin phi, cos phi).
  const Geometry g;
  const auto p = g.tof_projector();
  std::vector<double> point(g.n * g.n, 0.0);
  const std::size_t row = 20;  // y = -23
  const std::size_t col = 45;  // x = 27
  point[(row * g.n) + col] = 1.0;
  constexpr std::size_t k = Geometry::tof_bins;
  std::vector<double> got(g.views * g.bins * k);
  p.forward(point, g.all(), got);
  for (std::size_t v = 0; v < g.views; ++v) {
    std::size_t best = 0;
    double best_sum = -1.0;
    for (std::size_t b = 0; b < g.bins; ++b) {
      const auto first = got.begin() + static_cast<std::ptrdiff_t>(((v * g.bins) + b) * k);
      const double sum = std::accumulate(first, first + static_cast<std::ptrdiff_t>(k), 0.0);
      if (sum > best_sum) {
        best_sum = sum;
        best = b;
      }
    }
    double mean = 0.0;
    for (std::size_t j = 0; j < k; ++j) {
      const double center_mm = (static_cast<double>(j) - 10.0) * 100.0 * 0.299792458 / 2.0;
      mean += got[(((v * g.bins) + best) * k) + j] * center_mm;
    }
    mean /= best_sum;
    const double phi = g.phi[v * g.bins];
    const double want = (-g.x(col) * std::sin(phi)) + (g.x(row) * std::cos(phi));
    EXPECT_NEAR(mean, want, 1.5) << "view " << v;
  }
}

TEST(TofProjector, TheThreadsDoNotChangeTheResult) {
  // REQ: SRS-REC-006, SRS-REC-007
  const Geometry g;
  const auto p = g.tof_projector();
  const std::size_t size = g.views * g.bins * Geometry::tof_bins;
  const auto x = random_vector(g.n * g.n, 23);
  const auto y = random_vector(size, 24);
  std::vector<double> f1(size), f4(size), b1(g.n * g.n), b4(g.n * g.n);
  p.forward(x, g.all(), f1, 1);
  p.forward(x, g.all(), f4, 4);
  EXPECT_EQ(f1, f4);
  p.back(y, g.all(), b1, 1);
  p.back(y, g.all(), b4, 4);
  for (std::size_t i = 0; i < b1.size(); ++i) {
    ASSERT_NEAR(b4[i], b1[i], 1e-12 * std::max(1.0, std::abs(b1[i]))) << "pixel " << i;
  }
}

TEST(TofProjector, RefusesATimingThatCannotBe) {
  // REQ: SRS-REC-005, SRS-REC-007
  const Geometry g;
  using recon::Tof;
  for (const Tof bad : {Tof{0, 100.0, 300.0}, Tof{5, 0.0, 300.0}, Tof{5, 100.0, -1.0},
                        Tof{5, std::nan(""), 300.0}}) {
    EXPECT_THROW(recon::JosephProjector(g.s, g.phi, g.views, g.bins, g.n, 2.0, bad),
                 std::invalid_argument);
  }
  // One bin is a projector without TOF, whatever the width.
  EXPECT_EQ(
      recon::JosephProjector(g.s, g.phi, g.views, g.bins, g.n, 2.0, Tof{1, 0.0, 0.0}).tof_bins(),
      1U);
  const auto p = g.tof_projector();
  std::vector<double> image(g.n * g.n), out(g.bins);  // missing the TOF bins
  EXPECT_THROW(p.forward(image, std::vector<std::size_t>{0}, out), std::invalid_argument);
  EXPECT_THROW(p.back(out, std::vector<std::size_t>{0}, image), std::invalid_argument);
}

}  // namespace
