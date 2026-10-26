// SPDX-License-Identifier: MIT
// MiniDAQ - the strict reader of JSON objects that every configuration file of MiniDAQ uses
// (Chapter 6): the acquisition configuration and the hardware description of Chapter 22.
// Internal to the config module.
#pragma once

#include <algorithm>
#include <charconv>
#include <set>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"

namespace minidaq::config::detail {

using nlohmann::json;

// Edit distance, for "did you mean" suggestions on unknown keys.
inline std::size_t distance(std::string_view a, std::string_view b) {
  std::vector<std::size_t> row(b.size() + 1);
  for (std::size_t j = 0; j <= b.size(); ++j) {
    row[j] = j;
  }
  for (std::size_t i = 1; i <= a.size(); ++i) {
    std::size_t diag = row[0];
    row[0] = i;
    for (std::size_t j = 1; j <= b.size(); ++j) {
      const std::size_t up = row[j];
      row[j] = std::min({row[j] + 1, row[j - 1] + 1, diag + (a[i - 1] == b[j - 1] ? 0U : 1U)});
      diag = up;
    }
  }
  return row[b.size()];
}

inline std::string escape_pointer(std::string_view key) {
  std::string out;
  for (const char c : key) {
    if (c == '~') {
      out += "~0";
    } else if (c == '/') {
      out += "~1";
    } else {
      out += c;
    }
  }
  return out;
}

// ObjectReader lives for one call of a parse function and refers to that call's
// JSON object and error list; references are the honest type for that.
// NOLINTBEGIN(cppcoreguidelines-avoid-const-or-ref-data-members)
// [snippet:reader]
// Reads one JSON object: each get() checks presence, type and range, records
// an error with the value's JSON Pointer instead of throwing, and remembers
// the key, so that finish() can report every key nobody asked for.
class ObjectReader {
 public:
  ObjectReader(const json& obj, std::string path, ConfigErrors& errors)
      : obj_{obj}, path_{std::move(path)}, errors_{errors} {
    if (!obj_.is_object()) {
      error(path_, "must be an object");
    }
  }

  // [snippet:reader_number]
  template <typename T>
  void get(std::string_view key, T& out, T lo, T hi) {
    const json* v = find(key);
    if (v == nullptr) {
      return;  // optional: keep the default
    }
    const std::string at = path_ + "/" + escape_pointer(key);
    if constexpr (std::is_floating_point_v<T>) {
      if (!v->is_number()) {
        return error(at, "must be a number");
      }
    } else if constexpr (std::is_signed_v<T>) {
      if (!v->is_number_integer()) {
        return error(at, "must be an integer");
      }
    } else {
      if (!v->is_number_unsigned()) {
        return error(at, "must be a non-negative integer");
      }
    }
    const T x = v->get<T>();
    if (!(x >= lo && x <= hi)) {  // also rejects NaN
      return error(at, "must be between " + json(lo).dump() + " and " + json(hi).dump());
    }
    out = x;
  }
  // [/snippet:reader_number]

  void get(std::string_view key, std::string& out, std::initializer_list<std::string_view> allowed = {}) {
    const json* v = find(key);
    if (v == nullptr) {
      return;
    }
    const std::string at = path_ + "/" + escape_pointer(key);
    if (!v->is_string()) {
      return error(at, "must be a string");
    }
    const auto& s = v->get_ref<const std::string&>();
    if (allowed.size() != 0 && std::find(allowed.begin(), allowed.end(), s) == allowed.end()) {
      std::string list;
      for (const auto a : allowed) {
        list += (list.empty() ? "\"" : ", \"") + std::string{a} + "\"";
      }
      return error(at, "must be one of " + list);
    }
    out = s;
  }

  // A nested object: returns nullptr if absent (defaults apply).
  const json* object(std::string_view key) { return find(key); }
  [[nodiscard]] std::string child(std::string_view key) const { return path_ + "/" + escape_pointer(key); }

  void finish() {
    if (!obj_.is_object()) {
      return;
    }
    for (const auto& [key, value] : obj_.items()) {
      if (used_.count(key) != 0) {
        continue;
      }
      std::string msg = "unknown key";
      std::string_view best;
      std::size_t best_d = 3;  // suggest only close matches
      for (const auto& k : known_) {
        const std::size_t d = distance(key, k);
        if (d < best_d) {
          best_d = d;
          best = k;
        }
      }
      if (!best.empty()) {
        msg += " (did you mean \"" + std::string{best} + "\"?)";
      }
      error(child(key), msg);
    }
  }

 private:
  const json* find(std::string_view key) {
    known_.emplace(key);
    used_.emplace(key);
    if (!obj_.is_object()) {
      return nullptr;
    }
    const auto it = obj_.find(key);
    return it == obj_.end() ? nullptr : &*it;
  }
  void error(const std::string& at, std::string msg) { errors_.push_back({at, std::move(msg)}); }

  const json& obj_;
  std::string path_;
  ConfigErrors& errors_;
  std::set<std::string, std::less<>> used_;
  std::set<std::string, std::less<>> known_;
};
// [/snippet:reader]
// NOLINTEND(cppcoreguidelines-avoid-const-or-ref-data-members)

inline bool parse_version(std::string_view s, int& major, int& minor) {
  const auto dot = s.find('.');
  if (dot == std::string_view::npos) {
    return false;
  }
  const auto a = s.substr(0, dot);
  const auto b = s.substr(dot + 1);
  const auto ra = std::from_chars(a.data(), a.data() + a.size(), major);
  const auto rb = std::from_chars(b.data(), b.data() + b.size(), minor);
  return !a.empty() && !b.empty() && ra.ec == std::errc{} && ra.ptr == a.data() + a.size() &&
         rb.ec == std::errc{} && rb.ptr == b.data() + b.size() && major >= 0 && minor >= 0;
}

}  // namespace minidaq::config::detail
