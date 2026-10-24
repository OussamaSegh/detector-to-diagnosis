// SPDX-License-Identifier: MIT
#include "minidaq/control/audit.hpp"

#include <chrono>
#include <cstdio>
#include <ctime>

namespace minidaq::control {

std::string utc_now_iso8601() {
  const auto now = std::chrono::system_clock::now();
  const std::time_t t = std::chrono::system_clock::to_time_t(now);
  const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count() % 1000;
  std::tm tm{};
  if (gmtime_r(&t, &tm) == nullptr) {
    return "time-unavailable";
  }
  char buf[32];
  // 19 characters + ".mmmZ" + NUL fit in 32 for any year below 10000; check anyway.
  const std::size_t n = std::strftime(buf, sizeof buf, "%Y-%m-%dT%H:%M:%S", &tm);
  if (n == 0 || std::snprintf(buf + n, sizeof buf - n, ".%03dZ", static_cast<int>(ms)) != 5) {
    return "time-unavailable";
  }
  return buf;
}

}  // namespace minidaq::control
