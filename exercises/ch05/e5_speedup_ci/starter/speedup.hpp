// SPDX-License-Identifier: MIT
// Exercise 5.5 starter: a confidence interval for a speedup.
#pragma once

#include <cstdint>
#include <span>

namespace ex {

struct Interval {
  double low = 0.0;
  double estimate = 0.0;  // median(before) / median(after)
  double high = 0.0;
};

// Speedup of `after` over `before`, both given as run times (lower is faster):
// the ratio of medians, with a percentile bootstrap interval at `confidence`.
// Throws std::invalid_argument if either side has fewer than 3 samples, a time
// is not positive, or confidence is not in (0, 1).
[[nodiscard]] Interval speedup_ci(std::span<const double> before, std::span<const double> after,
                                  double confidence = 0.95, int resamples = 10'000, std::uint64_t seed = 1);

}  // namespace ex
