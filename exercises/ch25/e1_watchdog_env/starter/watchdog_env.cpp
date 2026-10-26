// SPDX-License-Identifier: MIT
#include "watchdog_env.hpp"

namespace sdwatch {

WatchdogSettings watchdog_settings(const char* usec, const char* pid, std::int64_t self) {
  // TODO: follow the rules in the header. This version trusts every value it is given.
  (void)pid;
  (void)self;
  if (usec == nullptr) {
    return {};
  }
  const auto us = std::chrono::microseconds{std::stoll(usec)};
  return {Watchdog::on, us, us};
}

std::optional<std::vector<std::pair<std::string, std::string>>> parse_notification(
    std::string_view datagram) {
  // TODO: split into lines, skip empty ones, and check every key.
  std::vector<std::pair<std::string, std::string>> out;
  const auto eq = datagram.find('=');
  out.emplace_back(std::string{datagram.substr(0, eq)}, std::string{datagram.substr(eq + 1)});
  return out;
}

}  // namespace sdwatch
