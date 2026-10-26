// SPDX-License-Identifier: MIT
// Exercise 25.1: what systemd asks of a service, read from its environment and its messages.
#pragma once

#include <chrono>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace sdwatch {

enum class Watchdog : std::uint8_t { off, on, invalid };

struct WatchdogSettings {
  Watchdog state = Watchdog::off;
  std::chrono::microseconds interval{0};    // WATCHDOG_USEC: a ping is due within this
  std::chrono::microseconds ping_every{0};  // how often the service pings: half the interval
};

// The watchdog settings for the process `self`, from the values of WATCHDOG_USEC and WATCHDOG_PID
// (nullptr when the variable is not set), as sd_watchdog_enabled(3) reads them:
// - no WATCHDOG_USEC: off;
// - WATCHDOG_USEC not a whole number of microseconds greater than 0 (digits only): invalid;
// - WATCHDOG_PID set and not a process number greater than 0 (digits only): invalid;
// - WATCHDOG_PID set to another process: off (the watchdog is meant for that one);
// - otherwise on, with the interval and the ping period.
// A number too large for 64 bits is invalid, not wrapped.
[[nodiscard]] WatchdogSettings watchdog_settings(const char* usec, const char* pid,
                                                 std::int64_t self);

// The assignments of a notification datagram, in order: "READY=1\nSTATUS=idle" gives
// {{"READY", "1"}, {"STATUS", "idle"}}. Empty lines are skipped (a message may end with a newline).
// Empty when any other line is not KEY=VALUE with a KEY of one or more uppercase letters, digits
// and underscores; a VALUE may be empty and may contain '='.
[[nodiscard]] std::optional<std::vector<std::pair<std::string, std::string>>> parse_notification(
    std::string_view datagram);

}  // namespace sdwatch
