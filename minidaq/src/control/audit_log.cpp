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
    : file_{std::fopen(path.c_str(), "a")}, sync_{sync} {}  // NOLINT(cppcoreguidelines-owning-memory): owned by file_

// [snippet:append]
void JsonLinesAuditLog::append(const AuditRecord& r) {
  const std::string line = to_json_line(r) + "\n";
  const std::lock_guard lock{mu_};
  if (file_ == nullptr) {
    return;
  }
  // fwrite may buffer: the error of a full disk often appears only at fflush.
  bool ok = std::fwrite(line.data(), 1, line.size(), file_.get()) == line.size();
  ok = std::fflush(file_.get()) == 0 && ok;
  if (sync_) {
    ok = ::fsync(::fileno(file_.get())) == 0 && ok;
  }
  if (!ok) {
    ++failed_writes_;
    std::clearerr(file_.get());  // so that the next record is tried, and judged, on its own
  }
}
// [/snippet:append]

std::uint64_t JsonLinesAuditLog::failed_writes() const {
  const std::lock_guard lock{mu_};
  return failed_writes_;
}

}  // namespace minidaq::control
