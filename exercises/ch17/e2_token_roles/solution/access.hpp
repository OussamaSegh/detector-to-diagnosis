// SPDX-License-Identifier: MIT
// Exercise 17.2: a token store and the role of each command, the core of
// minidaq/control/access.hpp without OpenSSL. The hash and the comparison are
// passed in, so that the tests can count the comparisons.
#pragma once

#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"

namespace ex172 {

enum class Role : std::uint8_t { none, observer, operator_ };

// The role a command needs: hello and auth none, status observer, every other
// command, including one this function has never heard of, operator.
[[nodiscard]] Role required_role(std::string_view cmd) noexcept;

// The hex digest of a token (SHA-256 in the product).
using Digest = std::function<std::string(std::string_view)>;
// Compares two digests of the same length in constant time (CRYPTO_memcmp in the product).
using Equal = std::function<bool(std::string_view, std::string_view)>;

struct Identity {
  std::string name;
  Role role = Role::none;
};

class TokenStore {
 public:
  // One token per line: "NAME ROLE SHA256", the role "observer" or "operator",
  // the digest 64 lowercase hex digits. Blank lines and lines starting with '#'
  // are ignored. Fails, with the line number, for any other line, for a name or
  // digest used twice, and for a file without tokens.
  [[nodiscard]] static minidaq::Expected<TokenStore, std::string> parse(std::string_view text, Digest digest,
                                                                       Equal equal);

  // The identity of a token, or nothing. A token is "mdq_" and 64 hex digits;
  // anything else is refused before it is hashed. Compares the digest with
  // every entry, so the time taken does not say which entry matched, or how
  // many entries there are before it.
  [[nodiscard]] std::optional<Identity> check(std::string_view token) const;
  [[nodiscard]] std::size_t size() const noexcept { return entries_.size(); }

 private:
  struct Entry {
    Identity identity;
    std::string digest;
  };
  TokenStore(Digest d, Equal e) : digest_{std::move(d)}, equal_{std::move(e)} {}
  Digest digest_;
  Equal equal_;
  std::vector<Entry> entries_;
};

}  // namespace ex172
