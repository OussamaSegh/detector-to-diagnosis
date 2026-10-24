// SPDX-License-Identifier: MIT
// Exercise 5.2 solution: the same source, with the hotspots removed (see NOTES.md).
#pragma once

#include <array>
#include <cstdint>
#include <span>

#include "minidaq/core/single.hpp"

namespace ex {

using minidaq::Single;

struct SourceConfig {
  double rate_hz = 10e6;          // Poisson rate of primary singles
  double pair_fraction = 0.3;     // probability that a primary gets a partner
  std::int64_t pair_spread_ps = 500;
  std::uint32_t crystals = 32'768;  // crystal ids 0 .. crystals - 1
  std::uint32_t crystals_per_ring = 512;
  std::uint64_t seed = 1;
};

// xoshiro256** by Blackman and Vigna (public domain reference algorithm):
// small state, a few cycles per number, and good statistical quality.
class Xoshiro256 {
 public:
  explicit Xoshiro256(std::uint64_t seed) noexcept;
  std::uint64_t next() noexcept {
    const std::uint64_t result = rotl(s_[1] * 5, 7) * 9;
    const std::uint64_t t = s_[1] << 17;
    s_[2] ^= s_[0];
    s_[3] ^= s_[1];
    s_[1] ^= s_[2];
    s_[0] ^= s_[3];
    s_[2] ^= t;
    s_[3] = rotl(s_[3], 45);
    return result;
  }
  // Uniform in [0, 1), 53 random bits.
  double unit() noexcept { return static_cast<double>(next() >> 11) * 0x1.0p-53; }
  // Uniform integer in [0, n) by multiply-shift (Lemire), no division.
  std::uint32_t below(std::uint32_t n) noexcept {
    return static_cast<std::uint32_t>(((next() >> 32) * n) >> 32);
  }

 private:
  static std::uint64_t rotl(std::uint64_t x, int k) noexcept { return (x << k) | (x >> (64 - k)); }
  std::array<std::uint64_t, 4> s_{};
};

class EventSource {
 public:
  explicit EventSource(SourceConfig cfg);
  std::size_t generate(std::span<Single> out);

 private:
  float normal() noexcept;

  SourceConfig cfg_;
  Xoshiro256 rng_;
  double mean_gap_ps_;
  double t_ps_ = 0.0;
  bool pending_ = false;
  Single pending_single_{};
};

}  // namespace ex
