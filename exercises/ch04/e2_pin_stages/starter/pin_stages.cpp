// SPDX-License-Identifier: MIT
// Exercise 4.2 starter.
#include "pin_stages.hpp"

#include <sched.h>

namespace ex {

std::vector<int> parse_cpu_list(std::string_view text) {
  // TODO: split on ',', each item "N" or "A-B" with A <= B; trim whitespace.
  (void)text;
  return {};
}

StagePlacement assign_stage_cpus(std::span<const int> cpus) {
  // TODO: cpus[0] housekeeping; source, decode, sort get cpus[1], cpus[2], cpus[3] if present.
  (void)cpus;
  return {};
}

minidaq::rt::RtProfile make_profile(const StagePlacement& placement, bool fifo) {
  // TODO: lock memory, prefault 256 KiB, copy the CPUs, FIFO only for dedicated stages.
  (void)placement;
  (void)fifo;
  return {};
}

std::vector<int> allowed_cpus() {
  std::vector<int> out;
  cpu_set_t set;
  CPU_ZERO(&set);
  if (sched_getaffinity(0, sizeof set, &set) == 0) {
    for (std::size_t c = 0; c < CPU_SETSIZE; ++c) {
      if (CPU_ISSET(c, &set)) {
        out.push_back(static_cast<int>(c));
      }
    }
  }
  return out;
}

}  // namespace ex
