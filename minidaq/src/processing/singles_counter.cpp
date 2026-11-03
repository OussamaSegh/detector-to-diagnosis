// SPDX-License-Identifier: MIT
#include "minidaq/processing/singles_counter.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace minidaq {

SinglesCounter::SinglesCounter(double energy_low_kev, double energy_high_kev)
    : lo_{energy_low_kev},
      hi_{energy_high_kev},
      counts_{std::make_unique<std::atomic<std::uint64_t>[]>(crystals)},
      block_counts_{std::make_unique<std::atomic<std::uint64_t>[]>(blocks)} {}

// REQ: SRS-COR-001
void SinglesCounter::record(std::span<const Single> singles) noexcept {
  std::uint64_t n = 0;
  std::array<std::uint64_t, blocks> per_block{};
  std::int64_t first = first_ps_.load(std::memory_order_relaxed);
  std::int64_t last = last_ps_.load(std::memory_order_relaxed);
  bool any = false;
  for (const Single& s : singles) {
    if (!ScannerGeometry::valid(s.crystal)) {
      continue;
    }
    ++per_block[ScannerGeometry::block_of(s.crystal)];
    first = std::min(first, s.time.count());
    last = std::max(last, s.time.count());
    any = true;
    const auto e = static_cast<double>(s.energy.count());  // compared as the sorter compares it
    // Not "e < lo || e > hi", which lets NaN through (as in the sorter).
    // NOLINTNEXTLINE(readability-simplify-boolean-expr)
    if (!(e >= lo_ && e <= hi_)) {
      continue;
    }
    // One writer: a load and a store, not a read-modify-write (the photopeak monitor does the
    // same, Chapter 26). The 18,432 counters fit in L2 (147 KB).
    std::atomic<std::uint64_t>& c = counts_[s.crystal.value()];
    c.store(c.load(std::memory_order_relaxed) + 1, std::memory_order_relaxed);
    ++n;
  }
  if (!any) {
    return;
  }
  for (std::size_t b = 0; b < blocks; ++b) {
    if (per_block[b] != 0) {
      std::atomic<std::uint64_t>& c = block_counts_[b];
      c.store(c.load(std::memory_order_relaxed) + per_block[b], std::memory_order_relaxed);
    }
  }
  first_ps_.store(first, std::memory_order_relaxed);
  last_ps_.store(last, std::memory_order_relaxed);
  total_.store(total_.load(std::memory_order_relaxed) + n, std::memory_order_release);
}

// REQ: SRS-COR-002
SinglesCounter::Snapshot SinglesCounter::snapshot() const {
  Snapshot s;
  s.total = total_.load(std::memory_order_acquire);
  s.per_crystal.resize(crystals);
  for (std::size_t i = 0; i < crystals; ++i) {
    s.per_crystal[i] = counts_[i].load(std::memory_order_relaxed);
  }
  s.per_block.resize(blocks);
  for (std::size_t b = 0; b < blocks; ++b) {
    s.per_block[b] = block_counts_[b].load(std::memory_order_relaxed);
  }
  if (first_ps_.load(std::memory_order_relaxed) != std::numeric_limits<std::int64_t>::max()) {
    s.first_ps = first_ps_.load(std::memory_order_relaxed);
    s.last_ps = last_ps_.load(std::memory_order_relaxed);
  }
  return s;
}

}  // namespace minidaq
