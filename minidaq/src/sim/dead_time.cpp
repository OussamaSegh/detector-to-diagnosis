// SPDX-License-Identifier: MIT
#include "minidaq/sim/dead_time.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>

#include "minidaq/core/geometry.hpp"

namespace minidaq::sim {

std::string_view to_string(DeadTimeModel m) noexcept {
  switch (m) {
    case DeadTimeModel::none:
      return "none";
    case DeadTimeModel::non_paralyzable:
      return "non_paralyzable";
    case DeadTimeModel::paralyzable:
      return "paralyzable";
  }
  return "none";
}

Expected<DeadTimeModel, std::string> parse_dead_time_model(std::string_view s) {
  for (const auto m : {DeadTimeModel::none, DeadTimeModel::non_paralyzable, DeadTimeModel::paralyzable}) {
    if (s == to_string(m)) {
      return m;
    }
  }
  return Unexpected<std::string>{std::string{"dead time model must be one of none, non_paralyzable, paralyzable"}};
}

Expected<DeadTimeConfig, std::string> validate(const DeadTimeConfig& c) {
  if (c.model != DeadTimeModel::none && (c.tau <= Picoseconds{0} || c.tau > Picoseconds{100'000'000})) {
    return Unexpected<std::string>{std::string{"dead time tau must be in (0, 100 us]"}};
  }
  return c;
}

// [snippet:theory]
double recorded_rate(DeadTimeModel m, double n, double tau_s) noexcept {
  switch (m) {
    case DeadTimeModel::none:
      return n;
    case DeadTimeModel::non_paralyzable:
      return n / (1.0 + n * tau_s);
    case DeadTimeModel::paralyzable:
      return n * std::exp(-n * tau_s);
  }
  return n;
}

double true_rate(DeadTimeModel m, double recorded, double tau_s) noexcept {
  switch (m) {
    case DeadTimeModel::none:
      return recorded;
    case DeadTimeModel::non_paralyzable:
      // m = n / (1 + n tau)  =>  n = m / (1 - m tau), defined for m < 1 / tau.
      return recorded * tau_s < 1.0 ? recorded / (1.0 - recorded * tau_s) : std::numeric_limits<double>::quiet_NaN();
    case DeadTimeModel::paralyzable: {
      // Solve n exp(-n tau) = m on the branch n < 1 / tau. f(n) = n exp(-n tau) - m
      // is increasing and concave there, so Newton's method from n = m
      // (always below the root) climbs monotonically to it.
      if (recorded * tau_s > (1.0 + 1e-12) / std::numbers::e) {  // allow for rounding at the maximum
        return std::numeric_limits<double>::quiet_NaN();
      }
      double n = recorded;
      for (int i = 0; i < 100; ++i) {
        const double e = std::exp(-n * tau_s);
        const double f = n * e - recorded;
        const double df = e * (1.0 - n * tau_s);
        if (df <= 0.0) {
          break;  // at the maximum: n = 1 / tau
        }
        const double step = f / df;
        n -= step;
        if (std::abs(step) <= 1e-12 * n) {
          break;
        }
      }
      return std::min(n, 1.0 / tau_s);
    }
  }
  return recorded;
}
// [/snippet:theory]

DeadTime::DeadTime(const DeadTimeConfig& cfg) : cfg_{cfg} {
  if (auto v = validate(cfg); !v) {
    throw std::invalid_argument("DeadTimeConfig: " + v.error());
  }
  units_.resize(cfg.unit == DeadTimeUnit::block ? ScannerGeometry::num_blocks : ScannerGeometry::num_crystals);
}

std::size_t DeadTime::unit_of(const Single& s) const noexcept {
  return cfg_.unit == DeadTimeUnit::block ? ScannerGeometry::block_of(s.crystal) : s.crystal.value();
}

// [snippet:push]
void DeadTime::push(std::span<const TruthSingle> in, std::vector<TruthSingle>& out) {
  for (const TruthSingle& t : in) {
    ++stats_.singles_in;
    if (cfg_.model == DeadTimeModel::none) {
      ++stats_.recorded;
      out.push_back(t);
      continue;
    }
    const Picoseconds now = t.single.time;
    release_until(now, out);  // nothing that arrives from now on can change them
    Unit& u = units_[unit_of(t.single)];
    if (u.busy && now < u.busy_until) {
      ++stats_.lost;
      const std::size_t k = u.open - first_seq_;  // still held: its unit is busy
      if (cfg_.pileup) {
        ++stats_.piled_up;
        held_[k].single.energy = held_[k].single.energy + t.single.energy;
      }
      if (cfg_.model == DeadTimeModel::paralyzable) {
        u.busy_until = now + cfg_.tau;  // every arrival restarts the dead time
        held_until_[k] = u.busy_until;
      }
      continue;
    }
    ++stats_.recorded;
    u.busy = true;
    u.busy_until = now + cfg_.tau;
    u.open = first_seq_ + held_.size();
    held_.push_back(t);
    held_until_.push_back(u.busy_until);
  }
}
// [/snippet:push]

void DeadTime::release_until(Picoseconds now, std::vector<TruthSingle>& out) {
  // In arrival order, so the output stays in time order: an event waits for
  // any earlier event that is still open, even on another unit.
  while (!held_.empty() && held_until_.front() <= now) {
    out.push_back(held_.front());
    held_.pop_front();
    held_until_.pop_front();
    ++first_seq_;
  }
}

void DeadTime::flush(std::vector<TruthSingle>& out) {
  release_until(Picoseconds{std::numeric_limits<std::int64_t>::max()}, out);
  for (Unit& u : units_) {
    u = Unit{};
  }
}

}  // namespace minidaq::sim
