// SPDX-License-Identifier: MIT
#include "randoms.hpp"

#include <random>

namespace ex83 {

std::vector<std::int64_t> poisson_times_ps(double rate_hz, double duration_s, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::exponential_distribution<double> gap{rate_hz * 1e-12};
  std::vector<std::int64_t> t;
  t.reserve(static_cast<std::size_t>(rate_hz * duration_s * 1.01) + 16);
  double now = gap(rng);
  while (now < duration_s * 1e12) {
    t.push_back(static_cast<std::int64_t>(now));
    now += gap(rng);
  }
  return t;
}

// [snippet:count]
// Two pointers that only move forward: [lo, hi) is the range of b within tau
// of the current single in a. Each pointer crosses b once, so the whole count
// is O(|a| + |b|), however many pairs there are.
std::uint64_t count_pairs_within(std::span<const std::int64_t> a, std::span<const std::int64_t> b,
                                 std::int64_t tau_ps) {
  std::uint64_t pairs = 0;
  std::size_t lo = 0;
  std::size_t hi = 0;
  for (const std::int64_t t : a) {
    while (lo < b.size() && b[lo] < t - tau_ps) {
      ++lo;
    }
    if (hi < lo) {
      hi = lo;
    }
    while (hi < b.size() && b[hi] <= t + tau_ps) {
      ++hi;
    }
    pairs += hi - lo;
  }
  return pairs;
}
// [/snippet:count]

// [snippet:formula]
// A single in detector 1 pairs with any single of detector 2 in an interval of
// length 2 tau around it; detector 2 delivers S2 * 2 tau singles in such an
// interval on average, and detector 1 delivers S1 singles per second.
double expected_randoms_per_s(double s1, double s2, double tau_s) {
  return 2.0 * tau_s * s1 * s2;
}
// [/snippet:formula]

}  // namespace ex83
