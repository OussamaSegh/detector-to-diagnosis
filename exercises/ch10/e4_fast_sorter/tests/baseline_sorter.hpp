// SPDX-License-Identifier: MIT
// Exercise 10.4: the slow but correct sorter that the starter begins from
// (the starter is this code). The speed test measures your sorter against it.
#pragma once

#include <cmath>
#include <deque>
#include <functional>
#include <limits>
#include <numbers>
#include <span>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"

namespace ex104 {

class BaselineSorter {
 public:
  explicit BaselineSorter(const minidaq::SorterConfig& cfg) : cfg_{cfg} {}

  void push(std::span<const minidaq::Single> in, std::vector<minidaq::Coincidence>& out) {
    const std::function<void(const minidaq::Coincidence&)> emit = [&out](const minidaq::Coincidence& c) {
      out.push_back(c);
    };
    for (const minidaq::Single& s : in) {
      const auto e = static_cast<double>(s.energy.count());
      if (!(e >= cfg_.energy_low_kev && e <= cfg_.energy_high_kev)) {
        continue;
      }
      if (have_last_ && s.time < last_time_) {
        continue;  // out of order
      }
      have_last_ = true;
      last_time_ = s.time;
      buf_.push_back(s);
      close_ready(s.time, false, emit);
    }
  }

  void flush(std::vector<minidaq::Coincidence>& out) {
    const std::function<void(const minidaq::Coincidence&)> emit = [&out](const minidaq::Coincidence& c) {
      out.push_back(c);
    };
    close_ready(minidaq::Picoseconds{0}, true, emit);
    buf_.clear();
    opener_ = 0;
    have_last_ = false;
  }

 private:
  // Position of a crystal's front face, computed from its index.
  static void position(const minidaq::Single& s, double& x, double& y) {
    using G = minidaq::ScannerGeometry;
    const double angle = (static_cast<double>(G::transaxial_of(s.crystal)) + 0.5) * 2.0 * std::numbers::pi /
                         static_cast<double>(G::crystals_per_ring);
    x = G::inner_radius_mm * std::cos(angle);
    y = G::inner_radius_mm * std::sin(angle);
  }

  bool good(const minidaq::Single& a, const minidaq::Single& b) const {
    using G = minidaq::ScannerGeometry;
    const int sa = static_cast<int>(G::transaxial_of(a.crystal) / G::crystals_per_block_transaxial);
    const int sb = static_cast<int>(G::transaxial_of(b.crystal) / G::crystals_per_block_transaxial);
    const int d = std::abs(sa - sb);
    if (std::min(d, static_cast<int>(G::blocks_per_ring) - d) < static_cast<int>(cfg_.min_sector_difference)) {
      return false;
    }
    if (cfg_.fov_radius_mm > 0.0) {
      double ax = 0;
      double ay = 0;
      double bx = 0;
      double by = 0;
      position(a, ax, ay);
      position(b, bx, by);
      const double len = std::hypot(bx - ax, by - ay);
      if (len == 0.0 || std::abs(ax * by - ay * bx) / len > cfg_.fov_radius_mm) {
        return false;
      }
    }
    return true;
  }

  // Closes every window that is complete: rescans the buffer from the start.
  void close_ready(minidaq::Picoseconds now, bool all, const std::function<void(const minidaq::Coincidence&)>& emit) {
    const minidaq::Picoseconds horizon = cfg_.delay.count() > 0 ? cfg_.delay + cfg_.window : cfg_.window;
    while (opener_ < buf_.size() && (all || now - buf_[opener_].time > horizon)) {
      const minidaq::Single opener = buf_[opener_];
      std::vector<minidaq::Single> group;
      std::vector<minidaq::Single> delayed;
      std::size_t next = opener_;
      for (std::size_t i = 0; i < buf_.size(); ++i) {
        const minidaq::Picoseconds dt = buf_[i].time - opener.time;
        if (i >= opener_ && dt <= cfg_.window) {
          group.push_back(buf_[i]);
          next = i + 1;
        } else if (i > opener_ && cfg_.delay.count() > 0 && dt >= cfg_.delay && dt <= cfg_.delay + cfg_.window) {
          delayed.push_back(buf_[i]);
        }
      }
      resolve(group, minidaq::CoincidenceKind::prompt, emit);
      if (!delayed.empty()) {
        resolve_delayed(opener, delayed, emit);
      }
      opener_ = next;
    }
    while (opener_ > 0 && !buf_.empty()) {  // forget singles before the next opener
      buf_.pop_front();
      --opener_;
    }
  }

  void resolve(const std::vector<minidaq::Single>& g, minidaq::CoincidenceKind kind,
               const std::function<void(const minidaq::Coincidence&)>& emit) const {
    if (g.size() == 2) {
      if (good(g[0], g[1])) {
        emit(minidaq::Coincidence{g[0], g[1], kind});
      }
      return;
    }
    if (g.size() < 2 || cfg_.multiples == minidaq::MultiplesPolicy::kill_all) {
      return;
    }
    std::vector<minidaq::Coincidence> goods;
    for (std::size_t i = 0; i < g.size(); ++i) {
      for (std::size_t j = i + 1; j < g.size(); ++j) {
        if (good(g[i], g[j])) {
          goods.push_back(minidaq::Coincidence{g[i], g[j], kind});
        }
      }
    }
    pick(goods, emit);
  }

  void resolve_delayed(const minidaq::Single& o, const std::vector<minidaq::Single>& d,
                       const std::function<void(const minidaq::Coincidence&)>& emit) const {
    std::vector<minidaq::Coincidence> goods;
    for (const minidaq::Single& x : d) {
      if (good(o, x)) {
        goods.push_back(minidaq::Coincidence{o, x, minidaq::CoincidenceKind::delayed});
      }
    }
    if (d.size() == 1) {
      for (const auto& c : goods) {
        emit(c);
      }
      return;
    }
    if (cfg_.multiples != minidaq::MultiplesPolicy::kill_all) {
      pick(goods, emit);
    }
  }

  void pick(const std::vector<minidaq::Coincidence>& goods,
            const std::function<void(const minidaq::Coincidence&)>& emit) const {
    switch (cfg_.multiples) {
      case minidaq::MultiplesPolicy::kill_all:
        return;
      case minidaq::MultiplesPolicy::take_all_goods:
        for (const auto& c : goods) {
          emit(c);
        }
        return;
      case minidaq::MultiplesPolicy::keep_if_only_one_good:
        if (goods.size() == 1) {
          emit(goods.front());
        }
        return;
      case minidaq::MultiplesPolicy::take_winner_of_goods:
        break;
    }
    const minidaq::Coincidence* best = nullptr;
    float best_sum = -std::numeric_limits<float>::infinity();
    for (const auto& c : goods) {
      const float sum = c.first.energy.count() + c.second.energy.count();
      if (sum > best_sum) {
        best_sum = sum;
        best = &c;
      }
    }
    if (best != nullptr) {
      emit(*best);
    }
  }

  minidaq::SorterConfig cfg_;
  std::deque<minidaq::Single> buf_;
  std::size_t opener_ = 0;
  bool have_last_ = false;
  minidaq::Picoseconds last_time_{};
};

}  // namespace ex104
