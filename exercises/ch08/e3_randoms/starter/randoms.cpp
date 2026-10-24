// SPDX-License-Identifier: MIT
#include "randoms.hpp"

#include <random>

namespace ex83 {

std::vector<std::int64_t> poisson_times_ps(double rate_hz, double duration_s, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::exponential_distribution<double> gap{rate_hz * 1e-12};
  std::vector<std::int64_t> t;
  double now = gap(rng);
  while (now < duration_s * 1e12) {
    t.push_back(static_cast<std::int64_t>(now));
    now += gap(rng);
  }
  return t;
}

std::uint64_t count_pairs_within(std::span<const std::int64_t> a, std::span<const std::int64_t> b,
                                 std::int64_t tau_ps) {
  // TODO: this looks only forward from each single in a.
  std::uint64_t pairs = 0;
  std::size_t j = 0;
  for (const std::int64_t t : a) {
    while (j < b.size() && b[j] < t) {
      ++j;
    }
    for (std::size_t k = j; k < b.size() && b[k] - t <= tau_ps; ++k) {
      ++pairs;
    }
  }
  return pairs;
}

double expected_randoms_per_s(double s1, double s2, double tau_s) {
  return tau_s * s1 * s2;  // TODO: derive it
}

}  // namespace ex83
