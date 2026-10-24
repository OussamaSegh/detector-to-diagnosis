// SPDX-License-Identifier: MIT
// Exercise 4.1: parse cyclictest histogram output.
#pragma once

#include <cstdint>
#include <istream>
#include <optional>
#include <vector>

namespace ex {

struct CyclictestThread {
  std::vector<std::uint64_t> bins;  // bins[us] = samples with that latency
  std::uint64_t total = 0;          // "# Total:": in-range samples only
  std::uint64_t overflows = 0;      // samples above the histogram range
  std::int64_t min_us = 0;
  std::int64_t avg_us = 0;
  std::int64_t max_us = 0;
  [[nodiscard]] std::uint64_t samples() const noexcept { return total + overflows; }
};

struct CyclictestReport {
  std::vector<CyclictestThread> threads;
};

// Throws std::runtime_error("line N: ...") on inconsistent input.
[[nodiscard]] CyclictestReport parse_cyclictest(std::istream& in);

// Latency in microseconds at or below which `percent` percent of all samples
// (overflows included) fall; nullopt if that rank is among the overflows.
[[nodiscard]] std::optional<std::int64_t> percentile_us(const CyclictestThread& t, double percent);

}  // namespace ex
