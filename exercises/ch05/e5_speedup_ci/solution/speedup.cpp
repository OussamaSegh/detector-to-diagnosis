// SPDX-License-Identifier: MIT
// Exercise 5.5 solution.
#include "speedup.hpp"

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>
#include <vector>

namespace ex {
namespace {

double median(std::vector<double>& v) {
  const std::size_t mid = v.size() / 2;
  std::nth_element(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(mid), v.end());
  const double hi = v[mid];
  if (v.size() % 2 == 1) {
    return hi;
  }
  const double lo = *std::max_element(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(mid));
  return 0.5 * (lo + hi);
}

void check(std::span<const double> v, const char* what) {
  if (v.size() < 3) {
    throw std::invalid_argument(std::string{what} + ": need at least 3 samples");
  }
  for (const double x : v) {
    if (!(x > 0.0) || !std::isfinite(x)) {
      throw std::invalid_argument(std::string{what} + ": times must be positive and finite");
    }
  }
}

}  // namespace

// [snippet:bootstrap]
Interval speedup_ci(std::span<const double> before, std::span<const double> after, double confidence,
                    int resamples, std::uint64_t seed) {
  check(before, "before");
  check(after, "after");
  if (!(confidence > 0.0 && confidence < 1.0) || resamples < 100) {
    throw std::invalid_argument("confidence must be in (0, 1) and resamples >= 100");
  }
  std::vector<double> b(before.begin(), before.end());
  std::vector<double> a(after.begin(), after.end());
  Interval out;
  out.estimate = median(b) / median(a);

  // Percentile bootstrap: pretend each sample is the population, draw new
  // samples of the same size with replacement, and see how much the ratio of
  // medians moves. Each side is resampled independently.
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::size_t> pick_b{0, before.size() - 1};
  std::uniform_int_distribution<std::size_t> pick_a{0, after.size() - 1};
  std::vector<double> ratios(static_cast<std::size_t>(resamples));
  for (auto& r : ratios) {
    for (auto& x : b) {
      x = before[pick_b(rng)];
    }
    for (auto& x : a) {
      x = after[pick_a(rng)];
    }
    r = median(b) / median(a);
  }
  std::sort(ratios.begin(), ratios.end());
  const double tail = (1.0 - confidence) / 2.0;
  const auto at = [&](double q) {
    const auto i = static_cast<std::size_t>(std::floor(q * static_cast<double>(ratios.size() - 1)));
    return ratios[i];
  };
  out.low = at(tail);
  out.high = at(1.0 - tail);
  return out;
}
// [/snippet:bootstrap]

}  // namespace ex
