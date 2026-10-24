// SPDX-License-Identifier: MIT
// Exercise 4.2 starter: CPU lists, stage placement and real-time profiles.
#pragma once

#include <array>
#include <span>
#include <string_view>
#include <vector>

#include "minidaq/rt/realtime.hpp"

namespace ex {

inline constexpr std::size_t num_stages = minidaq::rt::max_stages;  // source, decode, sort, pair, write
inline constexpr std::size_t num_busy_stages = 3;                   // source, decode, sort

struct StagePlacement {
  std::array<int, num_stages> cpu{-1, -1, -1, -1, -1};
  std::array<bool, num_stages> dedicated{};  // true: a busy stage alone on its CPU
};

// Linux cpulist format ("0-2,5"); sorted, unique. Throws std::invalid_argument.
[[nodiscard]] std::vector<int> parse_cpu_list(std::string_view text);

// cpus[0] is housekeeping; busy stages get dedicated CPUs from cpus[1..].
[[nodiscard]] StagePlacement assign_stage_cpus(std::span<const int> cpus);

[[nodiscard]] minidaq::rt::RtProfile make_profile(const StagePlacement& placement, bool fifo);

// CPUs this process may run on (sched_getaffinity).
[[nodiscard]] std::vector<int> allowed_cpus();

}  // namespace ex
