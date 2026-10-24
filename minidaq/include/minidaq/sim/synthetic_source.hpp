// SPDX-License-Identifier: MIT
// MiniDAQ - a minimal synthetic singles generator (Chapter 3).
//
// Not physics: Chapter 8 replaces it with the detector simulator. It produces
// a time-ordered stream of MDQ-P1 words with exponential inter-arrival times
// (a Poisson process at `rate_hz`) and, with probability `pair_fraction`, a
// second single within `pair_spread_ps` of the first on the opposite side of
// the ring, so the pipeline has something to pair. Deterministic for a seed.
#pragma once

#include <cstdint>
#include <random>
#include <span>

#include "minidaq/core/single.hpp"

namespace minidaq::sim {

struct SyntheticConfig {
  double rate_hz = 10e6;
  double pair_fraction = 0.3;
  std::int64_t pair_spread_ps = 500;
  std::uint64_t seed = 1;
};

class SyntheticSource {
 public:
  explicit SyntheticSource(SyntheticConfig cfg);
  // Fills `out` with packed words; returns the number written (always out.size()).
  std::size_t generate(std::span<std::uint64_t> out);
  [[nodiscard]] std::uint64_t generated() const noexcept { return generated_; }

 private:
  SyntheticConfig cfg_;
  std::mt19937_64 rng_;
  std::exponential_distribution<double> gap_;
  std::uniform_int_distribution<std::uint32_t> crystal_;
  std::normal_distribution<double> energy_;
  std::uniform_real_distribution<double> unit_;
  double t_ps_ = 0.0;
  bool pending_ = false;
  Single pending_single_{};
  std::uint64_t generated_ = 0;
};

}  // namespace minidaq::sim
