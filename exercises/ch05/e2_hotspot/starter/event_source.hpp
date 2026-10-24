// SPDX-License-Identifier: MIT
// Exercise 5.2: a synthetic event source that is too slow. Profile it, find
// the hotspot, and make it at least 3x faster without changing what it
// produces statistically (see README.md).
#pragma once

#include <cstdint>
#include <random>
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

class EventSource {
 public:
  explicit EventSource(SourceConfig cfg);
  // Fills `out` with time-ordered singles; returns out.size().
  std::size_t generate(std::span<Single> out);

 private:
  SourceConfig cfg_;
  std::mt19937_64 rng_;
  std::exponential_distribution<double> gap_;
  std::uniform_int_distribution<std::uint32_t> crystal_;
  std::normal_distribution<double> energy_;
  std::uniform_real_distribution<double> unit_;
  double t_ps_ = 0.0;
  bool pending_ = false;
  Single pending_single_{};
};

}  // namespace ex
