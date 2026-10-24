// SPDX-License-Identifier: MIT
// MiniDAQ - the audit port (Chapter 6): what the service reports about every
// control action, and the function it reports through. Where the records go
// (a JSON Lines file, a test's vector, later a database) is an adapter's job:
// see audit_log.hpp.
#pragma once

#include <functional>
#include <string>

namespace minidaq::control {

struct AuditRecord {
  std::string time_utc;  // ISO 8601 with milliseconds, e.g. 2027-03-15T09:30:00.123Z
  std::string who;       // "tcp:127.0.0.1:50422", "service", "test", ...
  std::string action;    // "configure", "start", "transition", "connect", ...
  std::string detail;    // free text or compact JSON
  bool ok = true;
};

using AuditSink = std::function<void(const AuditRecord&)>;

[[nodiscard]] std::string utc_now_iso8601();

}  // namespace minidaq::control
