// SPDX-License-Identifier: MIT
#include "watchdog_env.hpp"

#include <algorithm>
#include <charconv>
#include <system_error>

namespace sdwatch {

namespace {

// A whole number written in digits only: no sign, no spaces, no suffix, and no overflow.
std::optional<std::uint64_t> digits(const char* text) {
  const std::string_view s{text};
  if (s.empty() || !std::ranges::all_of(s, [](char c) { return c >= '0' && c <= '9'; })) {
    return std::nullopt;
  }
  std::uint64_t v = 0;
  const auto [end, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
  if (ec != std::errc{} || end != s.data() + s.size()) {
    return std::nullopt;  // too large for 64 bits
  }
  return v;
}

bool valid_key(std::string_view key) {
  return !key.empty() && std::ranges::all_of(key, [](char c) {
    return (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
  });
}

}  // namespace

WatchdogSettings watchdog_settings(const char* usec, const char* pid, std::int64_t self) {
  if (usec == nullptr) {
    return {};
  }
  const auto us = digits(usec);
  if (!us || *us == 0 ||
      *us > static_cast<std::uint64_t>(std::chrono::microseconds::max().count())) {
    return {Watchdog::invalid, {}, {}};
  }
  if (pid != nullptr) {
    const auto p = digits(pid);
    if (!p || *p == 0) {
      return {Watchdog::invalid, {}, {}};
    }
    if (static_cast<std::int64_t>(*p) != self) {
      return {};  // for another process, such as a wrapper's child
    }
  }
  const std::chrono::microseconds interval{static_cast<std::int64_t>(*us)};
  return {Watchdog::on, interval, interval / 2};
}

std::optional<std::vector<std::pair<std::string, std::string>>> parse_notification(
    std::string_view datagram) {
  std::vector<std::pair<std::string, std::string>> out;
  while (!datagram.empty()) {
    const auto nl = datagram.find('\n');
    const std::string_view line = datagram.substr(0, nl);
    datagram = nl == std::string_view::npos ? std::string_view{} : datagram.substr(nl + 1);
    if (line.empty()) {
      continue;
    }
    const auto eq = line.find('=');
    if (eq == std::string_view::npos || !valid_key(line.substr(0, eq))) {
      return std::nullopt;
    }
    out.emplace_back(std::string{line.substr(0, eq)}, std::string{line.substr(eq + 1)});
  }
  return out;
}

}  // namespace sdwatch
