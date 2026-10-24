// SPDX-License-Identifier: MIT
// Exercise 4.1 starter.
#include "cyclictest_report.hpp"

#include <stdexcept>

namespace ex {

CyclictestReport parse_cyclictest(std::istream& in) {
  // TODO: read line by line; histogram rows after "# Histogram", then the
  // "# Total:", "# Min/Avg/Max Latencies:" and "# Histogram Overflows:" lines.
  (void)in;
  throw std::runtime_error("parse_cyclictest: not implemented");
}

std::optional<std::int64_t> percentile_us(const CyclictestThread& t, double percent) {
  // TODO: 1-based rank over t.samples(), then walk the bins.
  (void)t;
  (void)percent;
  return std::nullopt;
}

}  // namespace ex
