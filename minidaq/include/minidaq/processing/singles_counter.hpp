// SPDX-License-Identifier: MIT
// MiniDAQ - the singles of each crystal, recorded for the corrections (Chapter 27).
//
// Two corrections need what the list-mode file does not hold: the randoms estimate from the
// singles, R_ij = 2 tau S_i S_j for the rates S_i and S_j of two crystals and a coincidence window
// of width tau, and the dead-time model, which works from each block's singles rate. Both need the
// singles that the coincidence sorter could have paired: those in its energy window. The dead time
// of a block's electronics, on the other hand, is spent on every event it records, whatever its
// energy. The decode stage counts both, after the calibration: the singles in the window per
// crystal, all singles per block, and the span of times they came from; the run record carries
// them (SRS-COR-001, SRS-COR-002).
#pragma once

#include <atomic>
#include <cstdint>
#include <limits>
#include <memory>
#include <span>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq {

// [snippet:counter]
class SinglesCounter {
 public:
  static constexpr std::size_t crystals = ScannerGeometry::num_crystals;
  static constexpr std::size_t blocks = ScannerGeometry::num_blocks;

  // Counts singles with energy_low_kev <= E <= energy_high_kev, the sorter's window.
  SinglesCounter(double energy_low_kev, double energy_high_kev);

  // One writer (the decode thread). Singles of an invalid crystal are not counted at all.
  void record(std::span<const Single> singles) noexcept;

  struct Snapshot {
    std::vector<std::uint64_t> per_crystal;  // crystals entries, in the window
    std::uint64_t total = 0;                 // their sum
    std::vector<std::uint64_t> per_block;    // blocks entries, every energy
    std::int64_t first_ps = 0;               // earliest and latest time of any single counted
    std::int64_t last_ps = 0;                // (both 0 if none)
  };
  // Any thread. While the writer runs, the counts may be from consecutive batches; after the
  // pipeline has stopped they are exact.
  [[nodiscard]] Snapshot snapshot() const;

  [[nodiscard]] double energy_low_kev() const noexcept { return lo_; }
  [[nodiscard]] double energy_high_kev() const noexcept { return hi_; }

 private:
  double lo_;
  double hi_;
  std::unique_ptr<std::atomic<std::uint64_t>[]> counts_;
  std::unique_ptr<std::atomic<std::uint64_t>[]> block_counts_;
  std::atomic<std::uint64_t> total_{0};
  std::atomic<std::int64_t> first_ps_{std::numeric_limits<std::int64_t>::max()};
  std::atomic<std::int64_t> last_ps_{std::numeric_limits<std::int64_t>::min()};
};
// [/snippet:counter]

}  // namespace minidaq
