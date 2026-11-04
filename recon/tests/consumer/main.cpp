// SPDX-License-Identifier: MIT
// Uses the installed recon::projector: projects a random image and backprojects a random
// sinogram, and checks <A x, y> = <x, A^T y> (the projector's defining property). Exit 0 and
// "ok" when it holds.
#include <recon/joseph.hpp>

#include <cmath>
#include <cstddef>
#include <cstdio>
#include <numbers>
#include <numeric>
#include <random>
#include <vector>

int main() {
  constexpr std::size_t views = 12;
  constexpr std::size_t bins = 31;
  constexpr std::size_t n = 24;
  constexpr double pixel_mm = 2.0;
  std::vector<double> s(views * bins);
  std::vector<double> phi(views * bins);
  for (std::size_t v = 0; v < views; ++v) {
    for (std::size_t b = 0; b < bins; ++b) {
      s[(v * bins) + b] = (static_cast<double>(b) - 15.0) * 1.5;
      phi[(v * bins) + b] = static_cast<double>(v) * std::numbers::pi / static_cast<double>(views);
    }
  }
  const recon::JosephProjector projector(s, phi, views, bins, n, pixel_mm);
  std::vector<std::size_t> all(views);
  std::iota(all.begin(), all.end(), std::size_t{0});

  std::mt19937_64 rng(32);
  std::uniform_real_distribution<double> u(0.0, 1.0);
  std::vector<double> x(n * n);
  std::vector<double> y(views * bins);
  for (auto& v : x) {
    v = u(rng);
  }
  for (auto& v : y) {
    v = u(rng);
  }
  std::vector<double> ax(views * bins);
  std::vector<double> aty(n * n);
  projector.forward(x, all, ax);
  projector.back(y, all, aty);
  const double lhs = std::inner_product(ax.begin(), ax.end(), y.begin(), 0.0);
  const double rhs = std::inner_product(x.begin(), x.end(), aty.begin(), 0.0);
  if (std::abs(lhs - rhs) > 1e-12 * std::abs(lhs) || lhs <= 0.0) {
    std::printf("adjoint test failed: %.17g against %.17g\n", lhs, rhs);
    return 1;
  }
  std::printf("ok: <Ax, y> = %.12g = <x, A^T y>\n", lhs);
  return 0;
}
