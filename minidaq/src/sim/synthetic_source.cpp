// SPDX-License-Identifier: MIT
#include "minidaq/sim/synthetic_source.hpp"

#include <cmath>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

namespace minidaq::sim {

SyntheticSource::SyntheticSource(SyntheticConfig cfg)
    : cfg_{cfg},
      rng_{cfg.seed},
      gap_{cfg.rate_hz * 1e-12},  // events per picosecond
      crystal_{0, ScannerGeometry::num_crystals - 1},
      energy_{511.0, 25.0},
      unit_{0.0, 1.0} {}

std::size_t SyntheticSource::generate(std::span<std::uint64_t> out) {
  using G = ScannerGeometry;
  for (auto& w : out) {
    Single s;
    if (pending_) {
      s = pending_single_;
      pending_ = false;
    } else {
      t_ps_ += gap_(rng_);
      s = Single{Picoseconds{static_cast<std::int64_t>(t_ps_)}, CrystalId{crystal_(rng_)},
                 KeV{static_cast<float>(energy_(rng_))}};
      if (unit_(rng_) < cfg_.pair_fraction) {
        // Partner: opposite side of the same ring, slightly later.
        const std::uint32_t ring = G::ring_of(s.crystal);
        const std::uint32_t opposite = (G::transaxial_of(s.crystal) + G::crystals_per_ring / 2) % G::crystals_per_ring;
        const auto dt = static_cast<std::int64_t>(unit_(rng_) * static_cast<double>(cfg_.pair_spread_ps));
        pending_single_ = Single{s.time + Picoseconds{dt}, G::make_crystal(ring, opposite),
                                 KeV{static_cast<float>(energy_(rng_))}};
        pending_ = true;
        // Keep the stream ordered: later singles start after the partner.
        t_ps_ = std::fmax(t_ps_, static_cast<double>(pending_single_.time.count()));
      }
    }
    w = packed::encode(s);
    ++generated_;
  }
  return out.size();
}

}  // namespace minidaq::sim
