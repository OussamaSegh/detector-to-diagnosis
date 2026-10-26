// SPDX-License-Identifier: MIT
#include "minidaq/rt/health.hpp"

#include <array>
#include <cstdio>
#include <utility>

namespace minidaq::rt {

void HealthMonitor::watch(std::string name, std::shared_ptr<const Heartbeat> beat,
                          std::chrono::milliseconds max_silence, Clock::time_point now) {
  watched_.push_back({std::move(name), std::move(beat), max_silence, now});
}

// [snippet:silent]
std::vector<Silence> HealthMonitor::silent(Clock::time_point now) const {
  std::vector<Silence> out;
  for (const auto& w : watched_) {
    const auto last = w.beat->last();
    // A beat from before watch() was called counts from watch(): the grace to start is the same.
    const auto from = last && *last > w.since ? *last : w.since;
    const auto quiet = std::chrono::duration_cast<std::chrono::milliseconds>(now - from);
    if (quiet > w.max_silence) {
      out.push_back({w.name, quiet, !last.has_value()});
    }
  }
  return out;
}
// [/snippet:silent]

std::string describe(const std::vector<Silence>& silences) {
  std::string out;
  for (const auto& s : silences) {
    if (!out.empty()) {
      out += "; ";
    }
    if (s.never_beat) {
      out += s.name + " never beat";
      continue;
    }
    std::array<char, 32> secs{};
    (void)std::snprintf(secs.data(), secs.size(), "%.1f",
                        static_cast<double>(s.silent_for.count()) / 1000.0);
    out += s.name + " silent for " + secs.data() + " s";
  }
  return out;
}

}  // namespace minidaq::rt
