// SPDX-License-Identifier: MIT
// MiniDAQ - the control protocol (Chapter 6): newline-delimited JSON over TCP.
//
// One request per line, one response per line, in order:
//
//   -> {"api": "2.1", "id": 1, "cmd": "auth", "token": "mdq_..."}
//   <- {"api": "2.1", "id": 1, "ok": true, "identity": "console", "role": "operator"}
//   -> {"api": "2.1", "id": 7, "cmd": "start"}
//   <- {"api": "2.1", "id": 7, "ok": true, "state": "running"}
//   <- {"api": "2.1", "id": 8, "ok": false, "state": "running",
//       "error": {"code": "illegal_transition", "message": "cannot start in state running"}}
//
// Commands: hello, auth (with "token"), configure (with "config"), start,
// stop, reset, status, diagnostics (with an optional "events" count). Compatibility rules (docs/adr/0003): a request whose
// "api" major version differs is refused with "unsupported_api"; unknown
// fields are ignored, so a newer client may send fields an older server does
// not know; new commands and new response fields are added only in minor
// versions; "id" is echoed unchanged so a client can match responses to
// requests. The status object is part of the versioned API too (ADR 0013):
// status_fields lists its top-level fields for this version.
//
// 1.0: Chapter 6. 1.1: Chapter 16, the status fields of Chapters 9 to 15.
// 2.0: Chapter 17 (ADR 0014): a connection authenticates with "auth" before any
// command but hello; status needs an observer, the other commands an operator.
// 2.1: Chapter 21 (ADR 0016): diagnostics, for an observer: the build ID and the newest
// events of the flight recorder.
// 2.2: Chapter 22 (ADR 0017): status field "hardware", the front-end boards' slow control.
#pragma once

#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

#include "minidaq/control/access.hpp"
#include "minidaq/control/acquisition_service.hpp"

namespace minidaq::control {

inline constexpr std::string_view api_version = "2.2";

// diagnostics: how many flight-recorder events it returns without "events", and at most.
inline constexpr std::size_t diagnostics_default_events = 64;
inline constexpr std::size_t diagnostics_max_events = 1024;

// The top-level fields of `status` in this API version. A status has no other
// field. A field that is not `always` there appears while its part exists: a
// detector, a sink, a run (`recent_latency_ns` after the first interval).
// Adding a field means a new minor version (test StatusFieldsMatchTheApiVersion).
struct StatusField {
  std::string_view name;
  bool always;
};
// [snippet:status_fields]
inline constexpr std::array status_fields{
    StatusField{"state", true},           StatusField{"run_id", true},
    StatusField{"fault", true},           StatusField{"config", true},
    StatusField{"detector", true},        StatusField{"sink", true},
    StatusField{"integrity", true},       // 1.1: Chapter 15, risk control RC-01
    StatusField{"hardware", true},        // 2.2: Chapter 22, null without hardware
    StatusField{"detector_counters", false},  // 1.1: Chapter 9
    StatusField{"sink_counters", false},  // 1.1: Chapter 12
    StatusField{"run", false},            StatusField{"stages", false},
    StatusField{"latency_ns", false},     StatusField{"recent_latency_ns", false},
    StatusField{"late_singles", false},
    StatusField{"sorter", false},         // 1.1: Chapter 10
};
// [/snippet:status_fields]
inline constexpr std::size_t max_request_bytes = std::size_t{64} * 1024;

// [snippet:framer]
// Splits a byte stream into lines. TCP delivers bytes, not messages: one
// recv() may hold half a request or three of them.
class LineFramer {
 public:
  explicit LineFramer(std::size_t max_line = max_request_bytes) : max_line_{max_line} {}
  void feed(std::string_view bytes) { buffer_.append(bytes); }
  // The next complete line, without "\n" or "\r\n"; nullopt if none yet, or
  // after a line longer than the limit (then overflowed() is true and the
  // connection should be closed: there is no way to resynchronize safely).
  std::optional<std::string> next();
  [[nodiscard]] bool overflowed() const noexcept { return overflowed_; }

 private:
  std::size_t max_line_;
  std::string buffer_;
  std::size_t scanned_ = 0;  // bytes of buffer_ already searched for '\n'
  bool overflowed_ = false;
};
// [/snippet:framer]

// [snippet:session]
// One client connection, as the protocol sees it.
struct Session {
  std::string peer;   // "tcp:127.0.0.1:50422"
  Identity identity;  // role none until "auth" succeeds
  bool failed_auth = false;  // set by a refused "auth": the server closes the connection
  // For the audit trail: "console@tcp:127.0.0.1:50422", or the peer alone.
  [[nodiscard]] std::string who() const;
};
// [/snippet:session]

// Handles one request line and returns the response line (without "\n").
// Never throws: malformed input gets an error response. `tokens` checks "auth";
// without a token store, authentication is off and the session's identity is
// whatever the server gave it when the client connected.
[[nodiscard]] std::string handle_request(std::string_view line, AcquisitionService& service, Session& session,
                                         const TokenStore* tokens);

}  // namespace minidaq::control
