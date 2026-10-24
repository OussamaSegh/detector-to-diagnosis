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

#include <cstdint>
#include <cstdio>
#include <memory>
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

  [[nodiscard]] bool is_open() const noexcept { return file_ != nullptr; }
  void append(const AuditRecord& r);
  [[nodiscard]] AuditSink sink() {
    return [this](const AuditRecord& r) { append(r); };
  }
  // Records that could not be written completely (a full disk, an I/O error).
  // A lost record is not silent: the owner checks this and reports it.
  [[nodiscard]] std::uint64_t failed_writes() const;

 private:
  struct Closer {
    void operator()(std::FILE* f) const noexcept {
      // Every record was flushed when it was appended; a failure here cannot
      // lose a record that append() reported as written.
      (void)std::fclose(f);  // NOLINT(cppcoreguidelines-owning-memory): this deleter is the owner
    }
  };
  mutable std::mutex mu_;
  std::unique_ptr<std::FILE, Closer> file_;
  bool sync_;
  std::uint64_t failed_writes_ = 0;
};

}  // namespace minidaq::control
