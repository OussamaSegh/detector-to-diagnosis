// SPDX-License-Identifier: MIT
// MiniDAQ - heartbeats and the health of a process (Chapter 25).
//
// A process can be alive and useless: a thread waits forever on a lock, a register read never
// returns, and the process still answers signals and still has its sockets open. A service
// manager's watchdog (systemd's WatchdogSec) restarts a process that stops pinging it, but it
// cannot see inside: it is only as good as the decision to ping. The decision here: every loop
// that matters beats its own heartbeat once per pass, and the process pings the watchdog only
// while every heartbeat is recent. A loop that stops makes the process stop pinging, and the
// service manager restarts it.
//
// A heartbeat is one atomic time stamp, written by its loop and read by any thread; beat() is
// wait-free and costs one clock read, so a loop can call it on every pass.
#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace minidaq::rt {

// [snippet:heartbeat]
class Heartbeat {
 public:
  using Clock = std::chrono::steady_clock;
  void beat() noexcept { beat_at(Clock::now()); }
  void beat_at(Clock::time_point t) noexcept {
    last_ns_.store(t.time_since_epoch().count(), std::memory_order_release);
  }
  // When it last beat, or empty if it never has.
  [[nodiscard]] std::optional<Clock::time_point> last() const noexcept {
    const auto ns = last_ns_.load(std::memory_order_acquire);
    if (ns == never) {
      return std::nullopt;
    }
    return Clock::time_point{Clock::duration{ns}};
  }

 private:
  static constexpr Clock::rep never = std::numeric_limits<Clock::rep>::min();
  std::atomic<Clock::rep> last_ns_{never};
};
// [/snippet:heartbeat]

// A heartbeat that has been silent for too long, and for how long.
struct Silence {
  std::string name;
  std::chrono::milliseconds silent_for{0};
  bool never_beat = false;
};

// [snippet:monitor]
class HealthMonitor {
 public:
  using Clock = Heartbeat::Clock;
  // Watches `beat`, which must beat at least every `max_silence`. A heartbeat that has never
  // beaten is measured from the time it was added: a loop gets max_silence to start.
  void watch(std::string name, std::shared_ptr<const Heartbeat> beat,
             std::chrono::milliseconds max_silence, Clock::time_point now = Clock::now());
  // The heartbeats silent for longer than allowed at `now`; empty when the process is healthy.
  [[nodiscard]] std::vector<Silence> silent(Clock::time_point now = Clock::now()) const;
  [[nodiscard]] std::size_t watched() const noexcept { return watched_.size(); }

 private:
  struct Watched {
    std::string name;
    std::shared_ptr<const Heartbeat> beat;
    std::chrono::milliseconds max_silence;
    Clock::time_point since;
  };
  std::vector<Watched> watched_;
};
// [/snippet:monitor]

// "slow control silent for 2.4 s; service never beat", for a log line or a STATUS message.
[[nodiscard]] std::string describe(const std::vector<Silence>& silences);

}  // namespace minidaq::rt
