// SPDX-License-Identifier: MIT
// Exercise 5.2 starter: correct, and slow.
#include "event_source.hpp"

#include <cmath>

namespace ex {

EventSource::EventSource(SourceConfig cfg)
    : cfg_{cfg},
      rng_{cfg.seed},
      gap_{cfg.rate_hz * 1e-12},
      crystal_{0, cfg.crystals - 1},
      energy_{511.0, 25.0},
      unit_{0.0, 1.0} {}

std::size_t EventSource::generate(std::span<Single> out) {
  for (auto& s : out) {
    if (pending_) {
      s = pending_single_;
      pending_ = false;
      continue;
    }
    t_ps_ += gap_(rng_);
    s = Single{minidaq::Picoseconds{static_cast<std::int64_t>(t_ps_)}, minidaq::CrystalId{crystal_(rng_)},
               minidaq::KeV{static_cast<float>(energy_(rng_))}};
    if (unit_(rng_) < cfg_.pair_fraction) {
      const std::uint32_t ring = s.crystal.value() / cfg_.crystals_per_ring;
      const std::uint32_t pos = s.crystal.value() % cfg_.crystals_per_ring;
      const std::uint32_t opposite = (pos + cfg_.crystals_per_ring / 2) % cfg_.crystals_per_ring;
      const auto dt = static_cast<std::int64_t>(unit_(rng_) * static_cast<double>(cfg_.pair_spread_ps));
      pending_single_ = Single{s.time + minidaq::Picoseconds{dt}, minidaq::CrystalId{ring * cfg_.crystals_per_ring + opposite},
                               minidaq::KeV{static_cast<float>(energy_(rng_))}};
      pending_ = true;
      t_ps_ = std::fmax(t_ps_, static_cast<double>(pending_single_.time.count()));
    }
  }
  return out.size();
}

}  // namespace ex
