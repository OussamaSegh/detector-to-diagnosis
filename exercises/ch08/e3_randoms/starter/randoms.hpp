// SPDX-License-Identifier: MIT
// Exercise 8.3: random coincidences between two independent detectors.
#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace ex83 {

// Arrival times in ps of a Poisson process at `rate_hz` over `duration_s`, sorted.
[[nodiscard]] std::vector<std::int64_t> poisson_times_ps(double rate_hz, double duration_s, std::uint64_t seed);

// Number of pairs (i, j) with |a[i] - b[j]| <= tau_ps. Both inputs sorted.
[[nodiscard]] std::uint64_t count_pairs_within(std::span<const std::int64_t> a, std::span<const std::int64_t> b,
                                               std::int64_t tau_ps);

// The expected randoms rate for singles rates s1, s2 (per s) and window |dt| <= tau_s.
[[nodiscard]] double expected_randoms_per_s(double s1, double s2, double tau_s);

}  // namespace ex83
