// SPDX-License-Identifier: MIT
#include "minidaq/processing/coincidence_sorter.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

#include "minidaq/core/geometry.hpp"

namespace minidaq {

namespace {

struct Named {
  std::string_view name;
  std::uint8_t value;
};
constexpr Named window_modes[] = {{"fixed", 0}, {"per_single", 1}};
constexpr Named policies[] = {
    {"kill_all", 0}, {"take_all_goods", 1}, {"take_winner_of_goods", 2}, {"keep_if_only_one_good", 3}};

template <typename E, std::size_t N>
Expected<E, std::string> parse_named(std::string_view s, const Named (&table)[N], std::string_view what) {
  std::string known;
  for (const auto& n : table) {
    if (n.name == s) {
      return static_cast<E>(n.value);
    }
    known += known.empty() ? "" : ", ";
    known += n.name;
  }
  return Unexpected<std::string>{std::string{what} + " must be one of " + known};
}

constexpr Picoseconds max_window{1'000'000};   // 1 us
constexpr Picoseconds max_delay{1'000'000'000};  // 1 ms

}  // namespace

std::string_view to_string(WindowMode m) noexcept { return window_modes[static_cast<std::size_t>(m)].name; }
std::string_view to_string(MultiplesPolicy p) noexcept { return policies[static_cast<std::size_t>(p)].name; }
Expected<WindowMode, std::string> parse_window_mode(std::string_view s) {
  return parse_named<WindowMode>(s, window_modes, "window mode");
}
Expected<MultiplesPolicy, std::string> parse_multiples_policy(std::string_view s) {
  return parse_named<MultiplesPolicy>(s, policies, "multiples policy");
}

Expected<SorterConfig, std::string> validate(const SorterConfig& c) {
  if (c.window <= Picoseconds{0} || c.window > max_window) {
    return Unexpected<std::string>{std::string{"window must be in (0, 1 us]"}};
  }
  if (c.delay != Picoseconds{0} && (c.delay <= c.window || c.delay > max_delay)) {
    return Unexpected<std::string>{std::string{"delay must be 0 (off) or more than the window and at most 1 ms"}};
  }
  // Written so that NaN fails every check.
  if (!(c.energy_low_kev >= 0.0) || !(c.energy_low_kev <= c.energy_high_kev) || !std::isfinite(c.energy_high_kev)) {
    return Unexpected<std::string>{std::string{"energy window must satisfy 0 <= low <= high, both finite"}};
  }
  if (c.min_sector_difference > ScannerGeometry::blocks_per_ring / 2) {
    return Unexpected<std::string>{std::string{"min_sector_difference must be at most half the sectors in a ring"}};
  }
  if (!(c.fov_radius_mm >= 0.0) || !(c.fov_radius_mm < ScannerGeometry::inner_radius_mm)) {
    return Unexpected<std::string>{std::string{"fov_radius_mm must be in [0, ring radius)"}};
  }
  return c;
}

namespace {
const SorterConfig& checked(const SorterConfig& c) {
  if (auto v = validate(c); !v) {
    throw std::invalid_argument("SorterConfig: " + v.error());
  }
  return c;
}
}  // namespace

CoincidenceSorter::CoincidenceSorter(const SorterConfig& cfg)
    : cfg_{checked(cfg)},
      horizon_{cfg.delay == Picoseconds{0} ? cfg.window : cfg.delay + cfg.window},
      fov_r2_{cfg.fov_radius_mm * cfg.fov_radius_mm} {
  buf_.reserve(8192);
}

// [snippet:good]
bool CoincidenceSorter::good(const Single& a, const Single& b) const noexcept {
  using G = ScannerGeometry;
  const std::uint32_t ta = G::transaxial_of(a.crystal);
  const std::uint32_t tb = G::transaxial_of(b.crystal);
  const std::uint32_t sa = ta / G::crystals_per_block_transaxial;
  const std::uint32_t sb = tb / G::crystals_per_block_transaxial;
  const std::uint32_t d = sa > sb ? sa - sb : sb - sa;
  if (std::min(d, G::blocks_per_ring - d) < cfg_.min_sector_difference) {
    return false;
  }
  if (fov_r2_ > 0.0) {
    // Distance from the axis to the line through the two crystal faces:
    // |p x q| / |q - p|. Compared squared, so no square root and no division.
    const Point2 p = crystal_xy_table[ta];
    const Point2 q = crystal_xy_table[tb];
    const double cross = p.x * q.y - p.y * q.x;
    const double dx = q.x - p.x;
    const double dy = q.y - p.y;
    const double len2 = dx * dx + dy * dy;
    if (len2 == 0.0 || cross * cross > fov_r2_ * len2) {
      return false;  // same transaxial position: no transaxial line at all
    }
  }
  return true;
}
// [/snippet:good]

// [snippet:push]
void CoincidenceSorter::push(std::span<const Single> in, std::vector<Coincidence>& out) {
  for (const Single& s : in) {
    ++stats_.singles_in;
    const auto e = static_cast<double>(s.energy.count());
    if (!(e >= cfg_.energy_low_kev && e <= cfg_.energy_high_kev)) {  // NaN fails too
      ++stats_.energy_rejected;
      continue;
    }
    if (have_last_ && s.time < last_time_) {
      ++stats_.out_of_order;  // its window may already be closed: cannot be placed
      continue;
    }
    have_last_ = true;
    last_time_ = s.time;
    // Windows that this single proves complete close before it joins the buffer.
    close_ready(s.time, out);
    buf_.push_back(s);
  }
}
// [/snippet:push]

void CoincidenceSorter::flush(std::vector<Coincidence>& out) {
  while (opener_ < buf_.size()) {
    close_window(out);  // the run is over: every open window is complete
  }
  buf_.clear();
  first_ = opener_ = delayed_begin_ = 0;
  have_last_ = false;
}

// [snippet:close]
void CoincidenceSorter::close_ready(Picoseconds now, std::vector<Coincidence>& out) {
  // A window opened at t is complete once a single later than t + horizon has
  // arrived: input is in time order, so nothing else can still fall inside it.
  while (opener_ < buf_.size() && now - buf_[opener_].time > horizon_) {
    close_window(out);
  }
  if (first_ > 4096 && first_ * 2 > buf_.size()) {
    compact();
  }
}

void CoincidenceSorter::close_window(std::vector<Coincidence>& out) {
  const std::size_t o = opener_;
  const Picoseconds t = buf_[o].time;
  std::size_t end = o + 1;
  while (end < buf_.size() && buf_[end].time - t <= cfg_.window) {
    ++end;
  }
  resolve_prompts(o, end, out);
  if (cfg_.delay != Picoseconds{0}) {
    // The delayed window [t + delay, t + delay + window] moves forward with
    // the openers, so its start index only ever increases.
    std::size_t b = std::max(delayed_begin_, o + 1);
    while (b < buf_.size() && buf_[b].time - t < cfg_.delay) {
      ++b;
    }
    std::size_t e = b;
    while (e < buf_.size() && buf_[e].time - t <= cfg_.delay + cfg_.window) {
      ++e;
    }
    resolve_delayed(o, b, e, out);
    delayed_begin_ = b;
  }
  opener_ = cfg_.mode == WindowMode::fixed ? end : o + 1;
  first_ = opener_;  // nothing before the next opener is needed again
}
// [/snippet:close]

// [snippet:resolve]
void CoincidenceSorter::resolve_prompts(std::size_t b, std::size_t e, std::vector<Coincidence>& out) {
  const std::size_t n = e - b;
  if (n == 1) {
    ++stats_.singles_alone;
    return;
  }
  if (n == 2) {
    ++stats_.pair_windows;
    if (good(buf_[b], buf_[b + 1])) {
      out.push_back(Coincidence{buf_[b], buf_[b + 1], CoincidenceKind::prompt});
      ++stats_.prompts;
    } else {
      ++stats_.geometry_rejected;
    }
    return;
  }
  ++stats_.multiple_windows;
  stats_.singles_in_multiples += n;
  if (cfg_.multiples == MultiplesPolicy::kill_all) {
    return;
  }
  std::size_t goods = 0;
  std::size_t wi = 0;
  std::size_t wj = 0;
  float best = -std::numeric_limits<float>::infinity();
  for (std::size_t i = b; i < e; ++i) {
    for (std::size_t j = i + 1; j < e; ++j) {
      if (!good(buf_[i], buf_[j])) {
        ++stats_.geometry_rejected;
        continue;
      }
      ++goods;
      if (cfg_.multiples == MultiplesPolicy::take_all_goods) {
        out.push_back(Coincidence{buf_[i], buf_[j], CoincidenceKind::prompt});
        ++stats_.prompts;
        ++stats_.prompts_from_multiples;
      } else if (const float sum = buf_[i].energy.count() + buf_[j].energy.count(); sum > best) {
        best = sum;  // ties keep the earlier pair
        wi = i;
        wj = j;
      }
    }
  }
  const bool keep = (cfg_.multiples == MultiplesPolicy::take_winner_of_goods && goods > 0) ||
                    (cfg_.multiples == MultiplesPolicy::keep_if_only_one_good && goods == 1);
  if (keep) {
    out.push_back(Coincidence{buf_[wi], buf_[wj], CoincidenceKind::prompt});
    ++stats_.prompts;
    ++stats_.prompts_from_multiples;
  }
}
// [/snippet:resolve]

void CoincidenceSorter::resolve_delayed(std::size_t o, std::size_t b, std::size_t e, std::vector<Coincidence>& out) {
  // The same rules as for prompts, applied to the pairs (opener, delayed single):
  // one delayed single is a pair, two or more make a delayed multiple.
  const std::size_t n = e - b;
  if (n == 0) {
    return;
  }
  if (n == 1 || cfg_.multiples != MultiplesPolicy::kill_all) {
    std::size_t goods = 0;
    std::size_t w = e;
    float best = -std::numeric_limits<float>::infinity();
    for (std::size_t j = b; j < e; ++j) {
      if (!good(buf_[o], buf_[j])) {
        continue;
      }
      ++goods;
      if (n == 1 || cfg_.multiples == MultiplesPolicy::take_all_goods) {
        out.push_back(Coincidence{buf_[o], buf_[j], CoincidenceKind::delayed});
        ++stats_.delayed;
      } else if (buf_[j].energy.count() > best) {
        best = buf_[j].energy.count();  // the opener is in every pair: compare the partner
        w = j;
      }
    }
    const bool keep = n > 1 && ((cfg_.multiples == MultiplesPolicy::take_winner_of_goods && goods > 0) ||
                                (cfg_.multiples == MultiplesPolicy::keep_if_only_one_good && goods == 1));
    if (keep) {
      out.push_back(Coincidence{buf_[o], buf_[w], CoincidenceKind::delayed});
      ++stats_.delayed;
    }
  }
}

void CoincidenceSorter::compact() {
  buf_.erase(buf_.begin(), buf_.begin() + static_cast<std::ptrdiff_t>(first_));
  opener_ -= first_;
  delayed_begin_ = delayed_begin_ > first_ ? delayed_begin_ - first_ : 0;
  first_ = 0;
}

}  // namespace minidaq
