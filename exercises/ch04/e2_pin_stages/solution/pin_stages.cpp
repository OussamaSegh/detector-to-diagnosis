// SPDX-License-Identifier: MIT
// Exercise 4.2 solution.
#include "pin_stages.hpp"

#include <sched.h>

#include <algorithm>
#include <charconv>
#include <stdexcept>
#include <string>

namespace ex {
namespace {

std::string_view trim(std::string_view s) {
  const auto ws = " \t\r\n";
  const auto b = s.find_first_not_of(ws);
  if (b == std::string_view::npos) {
    return {};
  }
  return s.substr(b, s.find_last_not_of(ws) - b + 1);
}

int to_cpu(std::string_view s, std::string_view whole) {
  int v = -1;
  const auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
  if (s.empty() || ec != std::errc{} || p != s.data() + s.size() || v < 0) {
    throw std::invalid_argument("bad cpulist: '" + std::string{whole} + "'");
  }
  return v;
}

}  // namespace

// [snippet:cpulist]
std::vector<int> parse_cpu_list(std::string_view text) {
  const std::string_view all = trim(text);
  std::vector<int> out;
  if (all.empty()) {
    return out;
  }
  std::size_t pos = 0;
  while (pos <= all.size()) {
    const std::size_t comma = std::min(all.find(',', pos), all.size());
    const std::string_view item = all.substr(pos, comma - pos);
    const std::size_t dash = item.find('-');
    if (dash == std::string_view::npos) {
      out.push_back(to_cpu(item, all));
    } else {
      const int lo = to_cpu(item.substr(0, dash), all);
      const int hi = to_cpu(item.substr(dash + 1), all);
      if (lo > hi) {
        throw std::invalid_argument("bad cpulist range: '" + std::string{item} + "'");
      }
      for (int c = lo; c <= hi; ++c) {
        out.push_back(c);
      }
    }
    pos = comma + 1;
  }
  std::sort(out.begin(), out.end());
  out.erase(std::unique(out.begin(), out.end()), out.end());
  return out;
}
// [/snippet:cpulist]

// [snippet:assign]
StagePlacement assign_stage_cpus(std::span<const int> cpus) {
  if (cpus.empty()) {
    throw std::invalid_argument("assign_stage_cpus: no CPUs");
  }
  StagePlacement p;
  const int housekeeping = cpus[0];
  p.cpu.fill(housekeeping);
  const std::size_t spare = cpus.size() - 1;
  for (std::size_t s = 0; s < num_busy_stages && s < spare; ++s) {
    p.cpu[s] = cpus[s + 1];
    p.dedicated[s] = true;
  }
  return p;
}
// [/snippet:assign]

minidaq::rt::RtProfile make_profile(const StagePlacement& placement, bool fifo) {
  constexpr std::array<int, num_stages> fifo_priority{80, 70, 70, 0, 0};  // pair and write are never dedicated
  minidaq::rt::RtProfile prof;
  prof.lock_memory = true;
  prof.prefault_stack_bytes = 256 * 1024;
  for (std::size_t s = 0; s < num_stages; ++s) {
    auto& st = prof.stages[s];
    st.cpu = placement.cpu[s];
    if (fifo && placement.dedicated[s]) {
      st.policy = minidaq::rt::SchedPolicy::fifo;
      st.priority = fifo_priority[s];
    }
  }
  return prof;
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
