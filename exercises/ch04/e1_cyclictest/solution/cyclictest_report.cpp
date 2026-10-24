// SPDX-License-Identifier: MIT
// Exercise 4.1 solution.
#include "cyclictest_report.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>

namespace ex {
namespace {

[[noreturn]] void fail(int line, const std::string& what) {
  throw std::runtime_error("line " + std::to_string(line) + ": " + what);
}

std::vector<std::int64_t> numbers(std::string_view rest, int line) {
  std::vector<std::int64_t> out;
  std::istringstream ss{std::string{rest}};
  std::int64_t v = 0;
  while (ss >> v) {
    out.push_back(v);
  }
  if (!ss.eof()) {
    fail(line, "expected numbers");
  }
  return out;
}

bool starts_with(std::string_view s, std::string_view prefix) { return s.substr(0, prefix.size()) == prefix; }

}  // namespace

// [snippet:parse]
CyclictestReport parse_cyclictest(std::istream& in) {
  CyclictestReport r;
  bool in_histogram = false;
  bool seen_histogram = false;
  bool seen_total = false;
  std::size_t next_row = 0;
  int n = 0;
  std::string line;

  // Per-thread summary lines: the label, then one value per thread.
  auto per_thread = [&](std::string_view rest, auto&& assign) {
    const auto v = numbers(rest, n);
    if (v.size() != r.threads.size()) {
      fail(n, "expected " + std::to_string(r.threads.size()) + " values");
    }
    for (std::size_t i = 0; i < v.size(); ++i) {
      assign(r.threads[i], v[i]);
    }
  };

  while (std::getline(in, line)) {
    ++n;
    const std::string_view s{line};
    if (s == "# Histogram") {
      in_histogram = seen_histogram = true;
      continue;
    }
    if (in_histogram && !s.empty() && s.front() != '#') {
      const auto v = numbers(s, n);
      if (v.size() < 2) {
        fail(n, "histogram row needs a latency and at least one count");
      }
      if (r.threads.empty()) {
        r.threads.resize(v.size() - 1);
      } else if (v.size() - 1 != r.threads.size()) {
        fail(n, "column count changed");
      }
      if (v[0] != static_cast<std::int64_t>(next_row)) {
        fail(n, "expected row " + std::to_string(next_row));
      }
      ++next_row;
      for (std::size_t i = 1; i < v.size(); ++i) {
        if (v[i] < 0) {
          fail(n, "negative count");
        }
        r.threads[i - 1].bins.push_back(static_cast<std::uint64_t>(v[i]));
      }
      continue;
    }
    in_histogram = false;
    if (!seen_histogram || r.threads.empty()) {
      continue;  // banner lines before the histogram
    }
    if (starts_with(s, "# Total:")) {
      per_thread(s.substr(8), [](CyclictestThread& t, std::int64_t v) { t.total = static_cast<std::uint64_t>(v); });
      seen_total = true;
    } else if (starts_with(s, "# Min Latencies:")) {
      per_thread(s.substr(16), [](CyclictestThread& t, std::int64_t v) { t.min_us = v; });
    } else if (starts_with(s, "# Avg Latencies:")) {
      per_thread(s.substr(16), [](CyclictestThread& t, std::int64_t v) { t.avg_us = v; });
    } else if (starts_with(s, "# Max Latencies:")) {
      per_thread(s.substr(16), [](CyclictestThread& t, std::int64_t v) { t.max_us = v; });
    } else if (starts_with(s, "# Histogram Overflows:")) {
      per_thread(s.substr(22),
                 [](CyclictestThread& t, std::int64_t v) { t.overflows = static_cast<std::uint64_t>(v); });
    }
  }

  if (r.threads.empty()) {
    fail(n, "no histogram found (did you pass -h?)");
  }
  if (!seen_total) {
    fail(n, "no '# Total:' line");
  }
  for (std::size_t i = 0; i < r.threads.size(); ++i) {
    const auto& t = r.threads[i];
    if (std::accumulate(t.bins.begin(), t.bins.end(), std::uint64_t{0}) != t.total) {
      fail(n, "thread " + std::to_string(i) + ": Total does not match the histogram rows");
    }
  }
  return r;
}
// [/snippet:parse]

// [snippet:percentile]
std::optional<std::int64_t> percentile_us(const CyclictestThread& t, double percent) {
  const std::uint64_t n = t.samples();
  if (n == 0) {
    return std::nullopt;
  }
  const double p = std::clamp(percent, 0.0, 100.0);
  auto rank = static_cast<std::uint64_t>(std::ceil(p / 100.0 * static_cast<double>(n) - 1e-9));
  rank = std::clamp<std::uint64_t>(rank, 1, n);
  std::uint64_t seen = 0;
  for (std::size_t us = 0; us < t.bins.size(); ++us) {
    seen += t.bins[us];
    if (seen >= rank) {
      return static_cast<std::int64_t>(us);
    }
  }
  return std::nullopt;  // the rank is among the overflows: larger than the histogram
}
// [/snippet:percentile]

}  // namespace ex
