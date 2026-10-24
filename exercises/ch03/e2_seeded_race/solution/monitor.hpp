// SPDX-License-Identifier: MIT
// Exercise 3.2 solution. See REPORT.md for the TSan reports and reasoning.
#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace ex {

struct EnergyWindow {
  float low_kev = 0.0F;
  float high_kev = 0.0F;
};

class EnergyMonitor {
 public:
  static constexpr std::size_t num_bins = 1024;

  // [snippet:fix]
  // Race 1 fix: counters are atomics. Relaxed is enough: each increment is
  // indivisible, and nobody infers anything about other memory from a count.
  void record(float energy_kev) noexcept {
    const auto bin = static_cast<std::size_t>(energy_kev < 0.0F ? 0.0F : energy_kev);
    bins_[bin < num_bins ? bin : num_bins - 1].fetch_add(1, std::memory_order_relaxed);
    total_.fetch_add(1, std::memory_order_relaxed);
  }

  // Race 2 fix: the window itself is published through one atomic. A window
  // is two floats (8 bytes), so it fits a lock-free std::atomic on every
  // platform we target, and readers can never see a mixed old/new window.
  // The flag is folded into the same atomic (high < low means "none yet").
  void publish_window(EnergyWindow w) noexcept { window_.store(w, std::memory_order_release); }

  [[nodiscard]] bool current_window(EnergyWindow& out) const noexcept {
    const EnergyWindow w = window_.load(std::memory_order_acquire);
    if (w.high_kev < w.low_kev) {
      return false;
    }
    out = w;
    return true;
  }
  // [/snippet:fix]

  [[nodiscard]] std::uint64_t total() const noexcept { return total_.load(std::memory_order_relaxed); }
  [[nodiscard]] std::uint64_t bin(std::size_t i) const noexcept { return bins_[i].load(std::memory_order_relaxed); }

 private:
  static_assert(std::atomic<EnergyWindow>::is_always_lock_free);
  std::array<std::atomic<std::uint64_t>, num_bins> bins_{};
  std::atomic<std::uint64_t> total_{0};
  std::atomic<EnergyWindow> window_{EnergyWindow{1.0F, 0.0F}};  // "no window" sentinel
};

}  // namespace ex
