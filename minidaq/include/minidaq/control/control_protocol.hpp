// SPDX-License-Identifier: MIT
// MiniDAQ - the control protocol (Chapter 6): newline-delimited JSON over TCP.
//
// One request per line, one response per line, in order:
//
//   -> {"api": "1.0", "id": 7, "cmd": "start"}
//   <- {"api": "1.0", "id": 7, "ok": true, "state": "running"}
//   <- {"api": "1.0", "id": 8, "ok": false, "state": "running",
//       "error": {"code": "illegal_transition", "message": "cannot start in state running"}}
//
// Commands: hello, configure (with "config"), start, stop, reset, status.
// Compatibility rules (docs/adr/0003): a request whose "api" major version
// differs is refused with "unsupported_api"; unknown fields are ignored, so a
// newer client may send fields an older server does not know; new commands
// and new response fields are added only in minor versions; "id" is echoed
// unchanged so a client can match responses to requests.
#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

#include "minidaq/control/acquisition_service.hpp"

namespace minidaq::control {

inline constexpr std::string_view api_version = "1.0";
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

// Handles one request line and returns the response line (without "\n").
// Never throws: malformed input gets an error response.
[[nodiscard]] std::string handle_request(std::string_view line, AcquisitionService& service, std::string_view who);

}  // namespace minidaq::control
