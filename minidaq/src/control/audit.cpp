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
  gmtime_r(&t, &tm);
  char buf[32];
  const std::size_t n = std::strftime(buf, sizeof buf, "%Y-%m-%dT%H:%M:%S", &tm);
  std::snprintf(buf + n, sizeof buf - n, ".%03dZ", static_cast<int>(ms));
  return buf;
}

}  // namespace minidaq::control
