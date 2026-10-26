// SPDX-License-Identifier: MIT
// MiniDAQ - the process's link to its service manager, and the watchdog (Chapter 25).
//
// On the installed system, systemd starts minidaq_server as a service of Type=notify
// (packaging/systemd/minidaq.service). The server then tells systemd when it is ready, when it
// is stopping, and, while it is healthy, that it is still alive. The protocol is sd_notify(3):
// one datagram of "NAME=value" lines to the unix socket that systemd names in NOTIFY_SOCKET.
// systemd guarantees the protocol to be stable and shows how to implement it without libsystemd,
// which this module does in a few system calls, so that MiniDAQ needs no new SOUP for it.
//
// The watchdog: with WatchdogSec= set, systemd puts the interval in WATCHDOG_USEC and kills the
// service (SIGABRT by default, which writes the crash report of Chapter 21) when no "WATCHDOG=1"
// has arrived for that long; Restart= then starts it again. Watchdog pings every half interval,
// as systemd recommends, and only while every heartbeat of the HealthMonitor is recent, so that
// a process whose loop has stopped is restarted although it is still running.
//
// Without NOTIFY_SOCKET (started from a shell or a test), every call does nothing and succeeds.
#pragma once

#include <chrono>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <thread>

#include "minidaq/core/expected.hpp"
#include "minidaq/rt/health.hpp"

namespace minidaq::control {

// [snippet:link]
class ServiceManagerLink {
 public:
  // From NOTIFY_SOCKET, WATCHDOG_USEC and WATCHDOG_PID, as sd_notify(3) and
  // sd_watchdog_enabled(3) read them. A WATCHDOG_PID that is not this process's turns the
  // watchdog off: the variables were meant for another process.
  [[nodiscard]] static Expected<ServiceManagerLink, std::string> from_environment();
  // To a given socket ("/run/x" or "@abstract"; empty: no manager), for tests.
  [[nodiscard]] static Expected<ServiceManagerLink, std::string> to(
      std::string socket, std::optional<std::chrono::microseconds> watchdog);

  [[nodiscard]] bool enabled() const noexcept { return !socket_.empty(); }
  // How long the manager waits for a ping before it kills the process; empty: no watchdog.
  [[nodiscard]] std::optional<std::chrono::microseconds> watchdog_interval() const noexcept {
    return watchdog_;
  }
  // Sends "NAME=value" lines in one datagram. 0, or the errno of the failure.
  [[nodiscard]] int notify(std::string_view lines) const;
  [[nodiscard]] int ready(std::string_view status) const;
  [[nodiscard]] int stopping(std::string_view status) const;
  [[nodiscard]] int status(std::string_view status) const;
  [[nodiscard]] int ping() const { return notify("WATCHDOG=1"); }
  [[nodiscard]] const std::string& socket() const noexcept { return socket_; }

 private:
  std::string socket_;
  std::optional<std::chrono::microseconds> watchdog_;
};
// [/snippet:link]

// [snippet:watchdog]
// A thread that pings the manager every half watchdog interval while the process is healthy,
// and reports each change of health (true: healthy again) with what is silent.
class Watchdog {
 public:
  using OnChange = std::function<void(bool healthy, const std::string& why)>;
  // Does nothing (no thread) when the link has no watchdog.
  Watchdog(const ServiceManagerLink& link, const rt::HealthMonitor& health, OnChange on_change);
  ~Watchdog();
  Watchdog(const Watchdog&) = delete;
  Watchdog& operator=(const Watchdog&) = delete;
  Watchdog(Watchdog&&) = delete;
  Watchdog& operator=(Watchdog&&) = delete;

  [[nodiscard]] bool running() const noexcept { return thread_.joinable(); }
  [[nodiscard]] std::chrono::microseconds period() const noexcept { return period_; }

 private:
  void run(const std::stop_token& st);

  const ServiceManagerLink& link_;
  const rt::HealthMonitor& health_;
  OnChange on_change_;
  std::chrono::microseconds period_{0};
  std::mutex mu_;
  std::condition_variable_any cv_;
  std::jthread thread_;
};
// [/snippet:watchdog]

}  // namespace minidaq::control
