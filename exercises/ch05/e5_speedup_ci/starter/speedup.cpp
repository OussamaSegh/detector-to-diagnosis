// SPDX-License-Identifier: MIT
// Exercise 5.5 starter.
#include "speedup.hpp"

namespace ex {

Interval speedup_ci(std::span<const double> before, std::span<const double> after, double confidence,
                    int resamples, std::uint64_t seed) {
  // TODO: validate, compute the estimate, then resample both sides with
  // replacement `resamples` times and take the percentiles of the ratios.
  (void)before, (void)after, (void)confidence, (void)resamples, (void)seed;
  return {};
}

}  // namespace ex
