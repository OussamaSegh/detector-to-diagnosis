// SPDX-License-Identifier: MIT
#include "minidaq/control/audit_log.hpp"

#include <unistd.h>

#include <chrono>
#include <ctime>

#include <nlohmann/json.hpp>

namespace minidaq::control {

std::string to_json_line(const AuditRecord& r) {
  const nlohmann::json j{{"time", r.time_utc}, {"who", r.who}, {"action", r.action}, {"detail", r.detail}, {"ok", r.ok}};
  // Replace invalid UTF-8 instead of throwing: the detail may echo client input.
  return j.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
}

JsonLinesAuditLog::JsonLinesAuditLog(const std::string& path, bool sync)
    : file_{std::fopen(path.c_str(), "a")}, sync_{sync} {}

JsonLinesAuditLog::~JsonLinesAuditLog() {
  if (file_ != nullptr) {
    std::fclose(file_);
  }
}

void JsonLinesAuditLog::append(const AuditRecord& r) {
  const std::string line = to_json_line(r) + "\n";
  const std::lock_guard lock{mu_};
  if (file_ == nullptr) {
    return;
  }
  std::fwrite(line.data(), 1, line.size(), file_);
  std::fflush(file_);
  if (sync_) {
    ::fsync(::fileno(file_));
  }
}

}  // namespace minidaq::control
