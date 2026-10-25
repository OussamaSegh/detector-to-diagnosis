// SPDX-License-Identifier: MIT
// Exercise 18.2: the subject of your property tests, a fixed-window coincidence
// sorter written like MiniDAQ's (minidaq/processing/coincidence_sorter.hpp)
// but smaller: no geometry cuts, no delayed window, two multiples policies.
// EX_MUTANT=0 is correct; 1 to 8 are seeded mistakes. Write your properties
// from the specification below, not from the mutants.
//
// Specification:
// - Energy gate: a single whose energy is outside [energy_low_kev,
//   energy_high_kev] (inclusive) is counted in energy_rejected and dropped.
// - Order: a single earlier than the previous accepted single is counted in
//   out_of_order and dropped.
// - Windows: the first accepted single not yet in a window opens one; every
//   accepted single at most `window` later than the opener (inclusive) joins
//   it. The next window opens at the first single after the group. Each single
//   is in exactly one window.
// - A window of one single is counted in singles_alone; of two, in
//   pair_windows, and the two are a prompt (earlier single first); of three or
//   more, in multiple_windows (its singles in singles_in_multiples), and the
//   policy decides: kill_all emits nothing, take_winner emits the pair with the
//   highest summed energy (on a tie the earlier pair: lower index of the first
//   single, then of the second).
// - push() may be called with batches of any size; the result does not depend
//   on them. flush() closes the open window at the end of a run.
// - Accounting: singles_in = energy_rejected + out_of_order + singles_alone
//   + 2 * pair_windows + singles_in_multiples, after flush().
#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

namespace ex {

using minidaq::Coincidence;
using minidaq::CoincidenceKind;
using minidaq::Picoseconds;
using minidaq::Single;

enum class Policy : std::uint8_t { kill_all, take_winner };

struct Config {
  Picoseconds window{4'000};
  double energy_low_kev = 435.0;
  double energy_high_kev = 585.0;
  Policy policy = Policy::kill_all;
};

struct Stats {
  std::uint64_t singles_in = 0;
  std::uint64_t energy_rejected = 0;
  std::uint64_t out_of_order = 0;
  std::uint64_t singles_alone = 0;
  std::uint64_t pair_windows = 0;
  std::uint64_t multiple_windows = 0;
  std::uint64_t singles_in_multiples = 0;
  std::uint64_t prompts = 0;
  friend bool operator==(const Stats&, const Stats&) = default;
};

class Sorter {
 public:
  explicit Sorter(const Config& cfg) : cfg_{cfg} {}

  void push(std::span<const Single> in, std::vector<Coincidence>& out) {
    for (const Single& s : in) {
      ++stats_.singles_in;
      const auto e = static_cast<double>(s.energy.count());
#if EX_MUTANT == 5
      if (!(e >= cfg_.energy_low_kev && e < cfg_.energy_high_kev)) {
#else
      if (!(e >= cfg_.energy_low_kev && e <= cfg_.energy_high_kev)) {
#endif
        ++stats_.energy_rejected;
        continue;
      }
#if EX_MUTANT != 6
      if (have_last_ && s.time < last_) {
        ++stats_.out_of_order;
        continue;
      }
#endif
      have_last_ = true;
      last_ = s.time;
#if EX_MUTANT == 1
      if (!open_.empty() && s.time - open_.front().time >= cfg_.window) {
#elif EX_MUTANT == 2
      if (!open_.empty() && s.time - open_.back().time > cfg_.window) {
#else
      if (!open_.empty() && s.time - open_.front().time > cfg_.window) {
#endif
        close(out, false);
      }
      open_.push_back(s);
    }
#if EX_MUTANT == 4
    open_.clear();  // the open window is lost between batches
#endif
  }

  void flush(std::vector<Coincidence>& out) {
    if (!open_.empty()) {
      close(out, true);
    }
    open_.clear();
    have_last_ = false;
  }

  [[nodiscard]] const Stats& stats() const noexcept { return stats_; }

 private:
  void close(std::vector<Coincidence>& out, [[maybe_unused]] bool at_flush) {
    const std::size_t n = open_.size();
    if (n == 1) {
#if EX_MUTANT == 7
      if (!at_flush) {
        ++stats_.singles_alone;
      }
#else
      ++stats_.singles_alone;
#endif
    } else if (n == 2) {
      ++stats_.pair_windows;
      out.push_back(Coincidence{open_[0], open_[1], CoincidenceKind::prompt});
      ++stats_.prompts;
#if EX_MUTANT == 3
      open_.erase(open_.begin());  // the second single opens the next window
      return;
#endif
    } else {
      ++stats_.multiple_windows;
      stats_.singles_in_multiples += n;
      if (cfg_.policy == Policy::take_winner) {
        std::size_t wi = 0;
        std::size_t wj = 1;
#if EX_MUTANT == 8
        float best = std::numeric_limits<float>::infinity();
#else
        float best = -std::numeric_limits<float>::infinity();
#endif
        for (std::size_t i = 0; i < n; ++i) {
          for (std::size_t j = i + 1; j < n; ++j) {
            const float sum = open_[i].energy.count() + open_[j].energy.count();
#if EX_MUTANT == 8
            if (sum < best) {
#else
            if (sum > best) {
#endif
              best = sum;
              wi = i;
              wj = j;
            }
          }
        }
        out.push_back(Coincidence{open_[wi], open_[wj], CoincidenceKind::prompt});
        ++stats_.prompts;
      }
    }
    open_.clear();
  }

  Config cfg_;
  std::vector<Single> open_;  // the singles of the open window
  bool have_last_ = false;
  Picoseconds last_{};
  Stats stats_{};
};

}  // namespace ex
