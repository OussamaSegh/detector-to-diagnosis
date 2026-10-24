// SPDX-License-Identifier: MIT
// Exercise 5.2 solution.
#include "event_source.hpp"

#include <cmath>
#include <cstring>

namespace ex {

Xoshiro256::Xoshiro256(std::uint64_t seed) noexcept {
  // splitmix64 expands the seed into the 256-bit state, as the authors recommend.
  for (auto& s : s_) {
    seed += 0x9e3779b97f4a7c15ULL;
    std::uint64_t z = seed;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    s = z ^ (z >> 31);
  }
}

namespace {

// ln(x) for 0 < x <= 1 without a library call: split x into 2^e * m with m in
// [1, 2), then ln(m) = 2 atanh((m - 1) / (m + 1)) by its series. Relative error
// below 1e-6 here; enough for exponential gaps in a simulator.
double fast_log(double x) noexcept {
  std::uint64_t bits = 0;
  std::memcpy(&bits, &x, sizeof bits);
  const auto e = static_cast<int>((bits >> 52) & 0x7ff) - 1023;
  bits = (bits & 0x000fffffffffffffULL) | 0x3ff0000000000000ULL;  // exponent 0: m in [1, 2)
  double m = 0.0;
  std::memcpy(&m, &bits, sizeof m);
  const double t = (m - 1.0) / (m + 1.0);
  const double t2 = t * t;
  const double series = t * (2.0 + t2 * (2.0 / 3 + t2 * (2.0 / 5 + t2 * (2.0 / 7 + t2 * (2.0 / 9 + t2 * (2.0 / 11))))));
  return static_cast<double>(e) * 0.6931471805599453 + series;
}

// Standard normal quantiles at 4,097 equally spaced probabilities, computed
// once by bisection on erf. Sampling is then a table lookup with linear
// interpolation: no log, no sqrt, no rejection loop. The table ends at the
// quantiles of 0.5 / 4097 and 1 - 0.5 / 4097 (about +-3.67 sigma), so the far
// tails (0.024% of samples) are clipped; acceptable for a test source, stated
// in NOTES.md.
constexpr std::size_t kTable = 4096;
const std::array<float, kTable + 1>& normal_table() {
  static const std::array<float, kTable + 1> t = [] {
    std::array<float, kTable + 1> q{};
    for (std::size_t i = 0; i <= kTable; ++i) {
      const double p = (static_cast<double>(i) + 0.5) / static_cast<double>(kTable + 1);
      double lo = -10.0;
      double hi = 10.0;
      for (int it = 0; it < 80; ++it) {
        const double mid = 0.5 * (lo + hi);
        (0.5 * std::erfc(-mid / std::sqrt(2.0)) < p ? lo : hi) = mid;
      }
      q[i] = static_cast<float>(0.5 * (lo + hi));
    }
    return q;
  }();
  return t;
}

}  // namespace

EventSource::EventSource(SourceConfig cfg) : cfg_{cfg}, rng_{cfg.seed}, mean_gap_ps_{1e12 / cfg.rate_hz} {
  (void)normal_table();  // build it now, not on the first generate()
}

float EventSource::normal() noexcept {
  const auto& t = normal_table();
  const double x = rng_.unit() * static_cast<double>(kTable);
  const auto i = static_cast<std::size_t>(x);
  const auto f = static_cast<float>(x - static_cast<double>(i));
  return t[i] + f * (t[i + 1] - t[i]);
}

// [snippet:generate]
std::size_t EventSource::generate(std::span<Single> out) {
  const std::uint32_t half = cfg_.crystals_per_ring / 2;
  for (auto& s : out) {
    if (pending_) {
      s = pending_single_;
      pending_ = false;
      continue;
    }
    // Exponential gap by inversion; 1 - u is in (0, 1], so the log is finite.
    t_ps_ -= mean_gap_ps_ * fast_log(1.0 - rng_.unit());
    const std::uint32_t crystal = rng_.below(cfg_.crystals);
    s = Single{minidaq::Picoseconds{static_cast<std::int64_t>(t_ps_)}, minidaq::CrystalId{crystal},
               minidaq::KeV{511.0F + 25.0F * normal()}};
    if (rng_.unit() < cfg_.pair_fraction) {
      const std::uint32_t ring = crystal / cfg_.crystals_per_ring;
      std::uint32_t opposite = crystal % cfg_.crystals_per_ring + half;
      opposite -= opposite >= cfg_.crystals_per_ring ? cfg_.crystals_per_ring : 0;
      const auto dt = static_cast<std::int64_t>(rng_.unit() * static_cast<double>(cfg_.pair_spread_ps));
      pending_single_ = Single{s.time + minidaq::Picoseconds{dt}, minidaq::CrystalId{ring * cfg_.crystals_per_ring + opposite},
                               minidaq::KeV{511.0F + 25.0F * normal()}};
      pending_ = true;
      t_ps_ = std::fmax(t_ps_, static_cast<double>(pending_single_.time.count()));
    }
  }
  return out.size();
}
// [/snippet:generate]

}  // namespace ex
