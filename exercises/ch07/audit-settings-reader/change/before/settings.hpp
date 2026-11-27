// SPDX-License-Identifier: MIT
// Exercise 7.6 (A): the acquisition settings file, "key = value" lines with
// comments after '#'. The file comes from outside the program: whatever it
// holds, reading it gives settings or an error with its reason, never an
// exception and never a crash.
#pragma once

#include <charconv>
#include <cstdint>
#include <string>
#include <string_view>
#include <system_error>

#include "minidaq/core/expected.hpp"

namespace ex76 {

struct Settings {
  std::string schema_version;
  std::int64_t run_seconds = 60;
};

namespace detail {
inline std::string_view trim(std::string_view s) {
  const auto b = s.find_first_not_of(" \t\r");
  if (b == std::string_view::npos) {
    return {};
  }
  return s.substr(b, s.find_last_not_of(" \t\r") - b + 1);
}
}  // namespace detail

inline minidaq::Expected<Settings, std::string> read_settings(std::string_view text) {
  using Error = minidaq::Unexpected<std::string>;
  Settings s;
  bool have_version = false;
  while (!text.empty()) {
    const auto eol = text.find('\n');
    std::string_view line = text.substr(0, eol);
    text = eol == std::string_view::npos ? std::string_view{} : text.substr(eol + 1);
    line = detail::trim(line.substr(0, line.find('#')));
    if (line.empty()) {
      continue;
    }
    const auto eq = line.find('=');
    if (eq == std::string_view::npos) {
      return Error{"a line without '=': " + std::string(line)};
    }
    const std::string_view key = detail::trim(line.substr(0, eq));
    const std::string_view value = detail::trim(line.substr(eq + 1));
    if (key == "schema_version") {
      s.schema_version = value;
      have_version = true;
    } else if (key == "run_seconds") {
      const auto [end, ec] =
          std::from_chars(value.data(), value.data() + value.size(), s.run_seconds);
      if (ec != std::errc{} || end != value.data() + value.size() || s.run_seconds <= 0) {
        return Error{"run_seconds is not a positive whole number: " + std::string(value)};
      }
    } else {
      return Error{"unknown key: " + std::string(key)};
    }
  }
  if (!have_version) {
    return Error{"no schema_version"};
  }
  if (s.schema_version != "2.2") {
    return Error{"schema_version '" + s.schema_version + "' is not 2.2"};
  }
  return s;
}

}  // namespace ex76
