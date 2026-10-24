// SPDX-License-Identifier: MIT
// MiniDAQ - audit trail of control actions (Chapter 6): the file adapter for
// the audit port (audit.hpp).
//
// Who did what, when, and with which result: every command, every state
// change, every client connection. One JSON object per line, appended and
// flushed as it happens, so a crash loses at most the line being written.
// The audit trail is control-plane only: the hot path reports through
// counters and histograms, which the control API reads, never through it.
#pragma once

#include <cstdio>
#include <functional>
#include <mutex>
#include <string>
#include <string_view>

#include "minidaq/control/audit.hpp"

namespace minidaq::control {

[[nodiscard]] std::string to_json_line(const AuditRecord& r);

class JsonLinesAuditLog {
 public:
  // Opens `path` for appending. If `sync` is set, each record is also
  // fsync()ed (slower; for systems where the audit trail is a record).
  explicit JsonLinesAuditLog(const std::string& path, bool sync = false);
  ~JsonLinesAuditLog();
  JsonLinesAuditLog(const JsonLinesAuditLog&) = delete;
  JsonLinesAuditLog& operator=(const JsonLinesAuditLog&) = delete;

  [[nodiscard]] bool is_open() const noexcept { return file_ != nullptr; }
  void append(const AuditRecord& r);
  [[nodiscard]] AuditSink sink() {
    return [this](const AuditRecord& r) { append(r); };
  }

 private:
  std::mutex mu_;
  std::FILE* file_ = nullptr;
  bool sync_;
};

}  // namespace minidaq::control
