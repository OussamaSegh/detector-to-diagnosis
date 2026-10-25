// SPDX-License-Identifier: MIT
// MiniDAQ - who may use the control API (Chapter 17, ADR 0014).
//
// A client proves who it is with a bearer token: 32 random bytes, written as
// "mdq_" and 64 hex digits. The server keeps only the tokens' SHA-256 hashes,
// each with a name and a role, so a stolen token file cannot be replayed. A
// token has 256 bits of entropy, so a fast hash is enough; slow password
// hashes exist for secrets that people choose.
//
// Two roles: an observer may read the status, an operator may also configure,
// start, stop and reset. Nothing here is on the acquisition's hot path.
#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"

namespace minidaq::control {

enum class Role : std::uint8_t { none, observer, operator_ };

[[nodiscard]] std::string_view to_string(Role r) noexcept;
[[nodiscard]] std::optional<Role> role_from_string(std::string_view s) noexcept;

// What a command needs: hello and auth nothing, status an observer, the rest an operator.
[[nodiscard]] Role required_role(std::string_view cmd) noexcept;

struct Identity {
  std::string name;
  Role role = Role::none;
};

// [snippet:tokens]
class TokenStore {
 public:
  // Reads {"tokens": [{"name", "role", "sha256"}]}. The file must belong to this
  // process's user and must not be writable by anyone else: whoever can write it
  // can add an operator.
  [[nodiscard]] static Expected<TokenStore, std::string> load(const std::filesystem::path& path);
  // A store with one token, for the token that the server makes at start-up.
  [[nodiscard]] static TokenStore single(std::string name, Role role, std::string_view token);

  // The identity of a token, or nothing. Compares the hash with every entry in
  // constant time, so the response time does not tell how close a guess was.
  [[nodiscard]] std::optional<Identity> check(std::string_view token) const;
  [[nodiscard]] std::size_t size() const noexcept { return entries_.size(); }

 private:
  struct Entry {
    Identity identity;
    std::string sha256;  // 32 raw bytes
  };
  std::vector<Entry> entries_;
};
// [/snippet:tokens]

// A new random token, "mdq_" and 64 hex digits, from the operating system's
// random generator; empty if it fails.
[[nodiscard]] std::string new_token();
// Lowercase hex SHA-256 of a token, as the token file stores it.
[[nodiscard]] std::string token_sha256_hex(std::string_view token);

// Where the server writes the token it makes at start-up, and where minidaq_ctl
// looks for it: $MINIDAQ_RUNTIME_DIR, else $XDG_RUNTIME_DIR/minidaq, else
// /tmp/minidaq-UID; the file is minidaq-PORT.token.
[[nodiscard]] std::filesystem::path default_token_path(std::uint16_t port);

// Writes a secret to a new file that only this user can read (mode 0600), in a
// directory that only this user can use (0700, created if missing). Refuses a
// directory that is a symbolic link or belongs to someone else: in a shared
// directory such as /tmp, another user could otherwise read or replace the file.
[[nodiscard]] Expected<std::filesystem::path, std::string> write_secret(const std::filesystem::path& path,
                                                                      std::string_view secret);
// Reads a secret written by write_secret, refusing a file that others can read.
[[nodiscard]] Expected<std::string, std::string> read_secret(const std::filesystem::path& path);

}  // namespace minidaq::control
