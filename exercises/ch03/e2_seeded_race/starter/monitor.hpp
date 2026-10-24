// SPDX-License-Identifier: MIT
// Exercise 3.2 starter: this code has two data races. Find them with TSan.
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
  static constexpr std::size_t num_bins = 1024;  // 1 keV bins, 0 to 1023 keV

  // Called concurrently by several decoder threads.
  void record(float energy_kev) noexcept {
    const auto bin = static_cast<std::size_t>(energy_kev < 0.0F ? 0.0F : energy_kev);
    bins_[bin < num_bins ? bin : num_bins - 1] += 1;
    total_ += 1;
  }

  // Called by the control thread.
  void publish_window(EnergyWindow w) noexcept {
    window_ = w;
    has_window_.store(true, std::memory_order_relaxed);
  }

  // Called by decoder threads; returns false until a window was published.
  [[nodiscard]] bool current_window(EnergyWindow& out) const noexcept {
    if (!has_window_.load(std::memory_order_relaxed)) {
      return false;
    }
    out = window_;
    return true;
  }

  [[nodiscard]] std::uint64_t total() const noexcept { return total_; }
  [[nodiscard]] std::uint64_t bin(std::size_t i) const noexcept { return bins_[i]; }

 private:
  std::array<std::uint64_t, num_bins> bins_{};
  std::uint64_t total_ = 0;
  EnergyWindow window_{};
  std::atomic<bool> has_window_{false};
};

}  // namespace ex
