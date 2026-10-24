// SPDX-License-Identifier: MIT
// Exercise 4.3 solution.
#include "stage_latencies.hpp"

#include <array>
#include <cmath>
#include <cstdio>
#include <stdexcept>

namespace ex {

StageLatencies::StageLatencies(std::vector<std::string> names) : names_{std::move(names)} {
  for (std::size_t i = 0; i < names_.size(); ++i) {
    histograms_.push_back(std::make_unique<minidaq::LatencyHistogram>());
  }
}

std::vector<HistogramSnapshot> StageLatencies::snapshot() const {
  std::vector<HistogramSnapshot> out(histograms_.size());
  for (std::size_t s = 0; s < histograms_.size(); ++s) {
    const auto& h = *histograms_[s];
    out[s].counts.resize(h.bucket_count());
    for (std::size_t i = 0; i < h.bucket_count(); ++i) {
      out[s].counts[i] = h.count_at(i);
    }
  }
  return out;
}

// [snippet:interval]
std::vector<IntervalStats> StageLatencies::interval(const std::vector<HistogramSnapshot>& before,
                                                    const std::vector<HistogramSnapshot>& after) const {
  if (before.size() != size() || after.size() != size()) {
    throw std::invalid_argument("interval: snapshots are for a different set of stages");
  }
  std::vector<IntervalStats> out(size());
  std::vector<std::uint64_t> delta;
  for (std::size_t s = 0; s < size(); ++s) {
    const auto& h = *histograms_[s];
    const auto& b = before[s].counts;
    const auto& a = after[s].counts;
    if (b.size() != h.bucket_count() || a.size() != h.bucket_count()) {
      throw std::invalid_argument("interval: snapshot has the wrong number of buckets");
    }
    // The count is the sum of bucket deltas: record() bumps the bucket before
    // the total, so a snapshot's count() could disagree with its buckets.
    delta.assign(a.size(), 0);
    std::uint64_t n = 0;
    std::size_t top = 0;
    for (std::size_t i = 0; i < a.size(); ++i) {
      if (a[i] < b[i]) {
        throw std::invalid_argument("interval: 'after' is older than 'before'");
      }
      delta[i] = a[i] - b[i];
      n += delta[i];
      if (delta[i] != 0) {
        top = i;
      }
    }
    IntervalStats& st = out[s];
    st.stage = names_[s];
    st.count = n;
    if (n == 0) {
      continue;
    }
    const auto at = [&](double percent) {
      auto rank = static_cast<std::uint64_t>(std::ceil(percent / 100.0 * static_cast<double>(n) - 1e-9));
      rank = std::max<std::uint64_t>(rank, 1);
      std::uint64_t seen = 0;
      for (std::size_t i = 0; i <= top; ++i) {
        seen += delta[i];
        if (seen >= rank) {
          return static_cast<std::int64_t>(h.highest_in(i));
        }
      }
      return static_cast<std::int64_t>(h.highest_in(top));
    };
    st.p50_ns = at(50.0);
    st.p99_ns = at(99.0);
    st.p999_ns = at(99.9);
    st.max_ns = static_cast<std::int64_t>(h.highest_in(top));
  }
  return out;
}
// [/snippet:interval]

namespace {

void append_json_string(std::string& out, const std::string& s) {
  out += '"';
  for (const char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\t': out += "\\t"; break;
      case '\r': out += "\\r"; break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          std::array<char, 8> buf{};
          std::snprintf(buf.data(), buf.size(), "\\u%04x", static_cast<unsigned>(c));
          out += buf.data();
        } else {
          out += c;
        }
    }
  }
  out += '"';
}

void append_us(std::string& out, std::int64_t ns) {
  std::array<char, 32> buf{};
  std::snprintf(buf.data(), buf.size(), "%.3f", static_cast<double>(ns) / 1000.0);
  out += buf.data();
}

}  // namespace

std::string to_json(const std::vector<IntervalStats>& stats, std::int64_t interval_ns) {
  std::string out = "{\"interval_ms\":";
  out += std::to_string(interval_ns / 1'000'000);
  out += ",\"stages\":[";
  for (std::size_t i = 0; i < stats.size(); ++i) {
    const auto& s = stats[i];
    out += i ? ",{\"name\":" : "{\"name\":";
    append_json_string(out, s.stage);
    out += ",\"count\":" + std::to_string(s.count);
    out += ",\"p50_us\":";
    append_us(out, s.p50_ns);
    out += ",\"p99_us\":";
    append_us(out, s.p99_ns);
    out += ",\"p999_us\":";
    append_us(out, s.p999_ns);
    out += ",\"max_us\":";
    append_us(out, s.max_ns);
    out += '}';
  }
  out += "]}";
  return out;
}

}  // namespace ex
