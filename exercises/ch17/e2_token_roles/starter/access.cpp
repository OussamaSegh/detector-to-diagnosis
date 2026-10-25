// SPDX-License-Identifier: MIT
// Exercise 17.2 starter. It compiles and works for the happy path; the tests in
// tests/test_access.cpp find what it gets wrong. Every TODO is a security defect.
#include "access.hpp"

#include <sstream>

namespace ex172 {

Role required_role(std::string_view cmd) noexcept {
  if (cmd == "configure" || cmd == "start" || cmd == "stop" || cmd == "reset") {
    return Role::operator_;
  }
  if (cmd == "status") {
    return Role::observer;
  }
  return Role::none;  // TODO: what does a command added next year need?
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
    fields >> name >> role >> hex;
    if (name.empty() || hex.empty()) {
      return minidaq::Unexpected{"line " + std::to_string(n) + ": expected NAME ROLE SHA256"};
    }
    // TODO: an unknown role, a digest that is not 64 lowercase hex digits, extra fields, duplicates.
    const Role r = role == "operator" ? Role::operator_ : Role::observer;
    store.entries_.push_back({{name, r}, hex});
  }
  return store;  // TODO: a file without tokens
}

std::optional<Identity> TokenStore::check(std::string_view token) const {
  // TODO: refuse what is not a token before hashing it.
  const std::string d = digest_(token);
  for (const auto& e : entries_) {
    if (d == e.digest) {  // TODO: the comparison and the loop both leak timing
      return e.identity;
    }
  }
  return std::nullopt;
}

}  // namespace ex172
