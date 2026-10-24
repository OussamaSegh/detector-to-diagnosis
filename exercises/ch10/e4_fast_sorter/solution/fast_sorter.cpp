// SPDX-License-Identifier: MIT
// Exercise 10.4, solution: the starter's algorithm with its hot spots removed.
// NOTES.md has the profile before and after, and the measured speed.
#include "fast_sorter.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <memory>

#include "minidaq/core/geometry.hpp"

namespace ex104 {

namespace {

using G = minidaq::ScannerGeometry;

// Sector of every transaxial crystal position, computed once.
constexpr std::array<std::uint8_t, G::crystals_per_ring> sector_table = [] {
  std::array<std::uint8_t, G::crystals_per_ring> t{};
  for (std::uint32_t i = 0; i < G::crystals_per_ring; ++i) {
    t[i] = static_cast<std::uint8_t>(i / G::crystals_per_block_transaxial);
  }
  return t;
}();

}  // namespace

struct FastSorter::Impl {
  explicit Impl(const minidaq::SorterConfig& c)
      : cfg{c},
        horizon{c.delay.count() > 0 ? c.delay + c.window : c.window},
        fov_r2{c.fov_radius_mm * c.fov_radius_mm} {
    buf.reserve(8192);
  }

  // [snippet:good]
  [[nodiscard]] bool good(const minidaq::Single& a, const minidaq::Single& b) const noexcept {
    const std::uint32_t ta = G::transaxial_of(a.crystal);
    const std::uint32_t tb = G::transaxial_of(b.crystal);
    const int d = std::abs(int{sector_table[ta]} - int{sector_table[tb]});
    if (std::min(d, int{G::blocks_per_ring} - d) < static_cast<int>(cfg.min_sector_difference)) {
      return false;
    }
    if (fov_r2 > 0.0) {
      // Table lookups instead of cos and sin; squared distances instead of
      // hypot and a division.
      const minidaq::Point2 p = minidaq::crystal_xy_table[ta];
      const minidaq::Point2 q = minidaq::crystal_xy_table[tb];
      const double cross = p.x * q.y - p.y * q.x;
      const double len2 = (q.x - p.x) * (q.x - p.x) + (q.y - p.y) * (q.y - p.y);
      if (len2 == 0.0 || cross * cross > fov_r2 * len2) {
        return false;
      }
    }
    return true;
  }
  // [/snippet:good]

  void push(std::span<const minidaq::Single> in, std::vector<minidaq::Coincidence>& out) {
    for (const minidaq::Single& s : in) {
      const auto e = static_cast<double>(s.energy.count());
      if (!(e >= cfg.energy_low_kev && e <= cfg.energy_high_kev)) {
        continue;
      }
      if (have_last && s.time < last_time) {
        continue;
      }
      have_last = true;
      last_time = s.time;
      // Only the windows this single completes, starting from the next
      // opener: no rescan of the buffer.
      while (opener < buf.size() && s.time - buf[opener].time > horizon) {
        close(out);
      }
      buf.push_back(s);
    }
    if (opener > 4096 && opener * 2 > buf.size()) {
      // Drop what no window needs any more, in one move, rather than a
      // pop_front per single.
      buf.erase(buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(opener));
      delayed_begin = delayed_begin > opener ? delayed_begin - opener : 0;
      opener = 0;
    }
  }

  void flush(std::vector<minidaq::Coincidence>& out) {
    while (opener < buf.size()) {
      close(out);
    }
    buf.clear();
    opener = delayed_begin = 0;
    have_last = false;
  }

  // [snippet:close]
  void close(std::vector<minidaq::Coincidence>& out) {
    const std::size_t o = opener;
    const minidaq::Picoseconds t = buf[o].time;
    std::size_t end = o + 1;
    while (end < buf.size() && buf[end].time - t <= cfg.window) {
      ++end;
    }
    // Prompts: the window is the index range [o, end); no copy into a group.
    if (end - o == 2) {
      if (good(buf[o], buf[o + 1])) {
        out.push_back(minidaq::Coincidence{buf[o], buf[o + 1], minidaq::CoincidenceKind::prompt});
      }
    } else if (end - o > 2 && cfg.multiples != minidaq::MultiplesPolicy::kill_all) {
      multiples(o, end, out);
    }
    if (cfg.delay.count() > 0) {
      // The delayed window only moves forward: start where the last one started.
      std::size_t b = std::max(delayed_begin, o + 1);
      while (b < buf.size() && buf[b].time - t < cfg.delay) {
        ++b;
      }
      std::size_t e = b;
      while (e < buf.size() && buf[e].time - t <= cfg.delay + cfg.window) {
        ++e;
      }
      delayed(o, b, e, out);
      delayed_begin = b;
    }
    opener = end;
  }
  // [/snippet:close]

  void multiples(std::size_t b, std::size_t e, std::vector<minidaq::Coincidence>& out) const {
    std::size_t goods = 0;
    std::size_t wi = 0;
    std::size_t wj = 0;
    float best = -std::numeric_limits<float>::infinity();
    for (std::size_t i = b; i < e; ++i) {
      for (std::size_t j = i + 1; j < e; ++j) {
        if (!good(buf[i], buf[j])) {
          continue;
        }
        ++goods;
        if (cfg.multiples == minidaq::MultiplesPolicy::take_all_goods) {
          out.push_back(minidaq::Coincidence{buf[i], buf[j], minidaq::CoincidenceKind::prompt});
        } else if (const float sum = buf[i].energy.count() + buf[j].energy.count(); sum > best) {
          best = sum;
          wi = i;
          wj = j;
        }
      }
    }
    if ((cfg.multiples == minidaq::MultiplesPolicy::take_winner_of_goods && goods > 0) ||
        (cfg.multiples == minidaq::MultiplesPolicy::keep_if_only_one_good && goods == 1)) {
      out.push_back(minidaq::Coincidence{buf[wi], buf[wj], minidaq::CoincidenceKind::prompt});
    }
  }

  void delayed(std::size_t o, std::size_t b, std::size_t e, std::vector<minidaq::Coincidence>& out) const {
    const std::size_t n = e - b;
    if (n == 0 || (n > 1 && cfg.multiples == minidaq::MultiplesPolicy::kill_all)) {
      return;
    }
    std::size_t goods = 0;
    std::size_t w = e;
    float best = -std::numeric_limits<float>::infinity();
    for (std::size_t j = b; j < e; ++j) {
      if (!good(buf[o], buf[j])) {
        continue;
      }
      ++goods;
      if (n == 1 || cfg.multiples == minidaq::MultiplesPolicy::take_all_goods) {
        out.push_back(minidaq::Coincidence{buf[o], buf[j], minidaq::CoincidenceKind::delayed});
      } else if (const float sum = buf[o].energy.count() + buf[j].energy.count(); sum > best) {
        best = sum;
        w = j;
      }
    }
    if (n > 1 && ((cfg.multiples == minidaq::MultiplesPolicy::take_winner_of_goods && goods > 0) ||
                  (cfg.multiples == minidaq::MultiplesPolicy::keep_if_only_one_good && goods == 1))) {
      out.push_back(minidaq::Coincidence{buf[o], buf[w], minidaq::CoincidenceKind::delayed});
    }
  }

  minidaq::SorterConfig cfg;
  minidaq::Picoseconds horizon;
  double fov_r2;
  std::vector<minidaq::Single> buf;  // accepted singles from the next opener on (plus a prefix until compaction)
  std::size_t opener = 0;
  std::size_t delayed_begin = 0;
  bool have_last = false;
  minidaq::Picoseconds last_time{};
};

FastSorter::FastSorter(const minidaq::SorterConfig& cfg) : impl_{std::make_unique<Impl>(cfg)} {}
FastSorter::~FastSorter() = default;
void FastSorter::push(std::span<const minidaq::Single> in, std::vector<minidaq::Coincidence>& out) {
  impl_->push(in, out);
}
void FastSorter::flush(std::vector<minidaq::Coincidence>& out) { impl_->flush(out); }

}  // namespace ex104
