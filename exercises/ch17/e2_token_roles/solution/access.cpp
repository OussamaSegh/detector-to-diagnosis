// SPDX-License-Identifier: MIT
#include "access.hpp"

#include <algorithm>
#include <sstream>

namespace ex172 {

namespace {

bool lower_hex(std::string_view s, std::size_t n) {
  return s.size() == n &&
         std::all_of(s.begin(), s.end(), [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); });
}

std::optional<Role> role_of(std::string_view s) {
  if (s == "observer") {
    return Role::observer;
  }
  if (s == "operator") {
    return Role::operator_;
  }
  return std::nullopt;  // never a default role: a typo must not grant anything
}

}  // namespace

Role required_role(std::string_view cmd) noexcept {
  if (cmd == "hello" || cmd == "auth") {
    return Role::none;
  }
  if (cmd == "status") {
    return Role::observer;
  }
  return Role::operator_;  // fail closed: a command added later is protected until someone decides
}

minidaq::Expected<TokenStore, std::string> TokenStore::parse(std::string_view text, Digest digest, Equal equal) {
  TokenStore store{std::move(digest), std::move(equal)};
  std::istringstream in{std::string{text}};
  std::string line;
  for (int n = 1; std::getline(in, line); ++n) {
    if (line.empty() || line[0] == '#') {
      continue;
    }
    std::istringstream fields{line};
    std::string name;
    std::string role;
    std::string hex;
    std::string extra;
    fields >> name >> role >> hex;
    const auto r = role_of(role);
    if (name.empty() || !r || !lower_hex(hex, 64) || (fields >> extra)) {
      return minidaq::Unexpected{"line " + std::to_string(n) + ": expected NAME observer|operator SHA256"};
    }
    for (const auto& e : store.entries_) {
      if (e.identity.name == name || e.digest == hex) {
        return minidaq::Unexpected{"line " + std::to_string(n) + ": name or token used twice"};
      }
    }
    store.entries_.push_back({{name, *r}, hex});
  }
  if (store.entries_.empty()) {
    return minidaq::Unexpected{std::string{"no tokens"}};
  }
  return store;
}

// [snippet:check]
std::optional<Identity> TokenStore::check(std::string_view token) const {
  constexpr std::string_view prefix = "mdq_";
  if (token.substr(0, prefix.size()) != prefix || !lower_hex(token.substr(prefix.size()), 64)) {
    return std::nullopt;
  }
  const std::string d = digest_(token);
  const Entry* found = nullptr;
  for (const auto& e : entries_) {  // no early exit
    if (d.size() == e.digest.size() && equal_(d, e.digest)) {
      found = &e;
    }
  }
  return found != nullptr ? std::optional<Identity>{found->identity} : std::nullopt;
}
// [/snippet:check]

}  // namespace ex172
