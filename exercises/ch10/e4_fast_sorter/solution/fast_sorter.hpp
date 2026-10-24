// SPDX-License-Identifier: MIT
// Exercise 10.4: a sorter fast enough for the throughput target.
#pragma once

#include <memory>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"

namespace ex104 {

// The same coincidences as minidaq::CoincidenceSorter for cfg.mode == fixed,
// in the same order, for any chunking of the input.
class FastSorter {
 public:
  explicit FastSorter(const minidaq::SorterConfig& cfg);
  ~FastSorter();
  FastSorter(const FastSorter&) = delete;
  FastSorter& operator=(const FastSorter&) = delete;
  FastSorter(FastSorter&&) = delete;
  FastSorter& operator=(FastSorter&&) = delete;
  void push(std::span<const minidaq::Single> in, std::vector<minidaq::Coincidence>& out);
  void flush(std::vector<minidaq::Coincidence>& out);

 private:
  struct Impl;  // in fast_sorter.cpp
  std::unique_ptr<Impl> impl_;
};

}  // namespace ex104
