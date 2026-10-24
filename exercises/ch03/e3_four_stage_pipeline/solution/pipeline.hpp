// SPDX-License-Identifier: MIT
// Exercise 3.3: four-stage pipeline interface (identical in starter and solution).
#pragma once

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <span>
#include <string_view>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/core/units.hpp"

namespace ex {

enum class Overflow { block, drop };

struct Config {
  std::size_t batch_size = 1024;
  std::size_t queue_batches = 16;
  minidaq::Picoseconds window{4'000};
  Overflow overflow = Overflow::block;
  std::chrono::microseconds write_delay{0};  // per batch, simulates a slow disk
};

struct StageReport {
  std::string_view name;
  std::uint64_t in = 0;
  std::uint64_t out = 0;
  std::uint64_t dropped = 0;   // lost to overflow (only decode, only with Overflow::drop)
  std::uint64_t filtered = 0;  // removed by the stage's logic: invalid words, unpaired singles
  double busy_seconds = 0.0;
  [[nodiscard]] double throughput() const noexcept {
    return busy_seconds > 0.0 ? static_cast<double>(in) / busy_seconds : 0.0;
  }
};

struct Result {
  std::vector<minidaq::Coincidence> coincidences;
  std::array<StageReport, 4> stages;  // decode, sort, pair, write
  double wall_seconds = 0.0;
};

using WriteCallback = std::function<void(std::span<const minidaq::Coincidence>)>;

Result run_pipeline(std::span<const std::uint64_t> words, const Config& cfg, const WriteCallback& on_write = {});

}  // namespace ex
