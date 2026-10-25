// SPDX-License-Identifier: MIT
// Exercise 17.5: the secure defaults of the control server, for IPv4 and IPv6.
#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace ex175 {

struct Security {
  bool tokens = false;                 // a token store is configured
  bool tls = false;                    // a TLS certificate and key are configured
  bool allow_unauthenticated = false;  // --no-auth
};

// True if `address`, a numeric IPv4 or IPv6 address, can be reached only from
// this machine: 127.0.0.0/8, ::1, or an IPv4-mapped loopback address
// (::ffff:127.x.y.z). A host name, a wildcard, or anything that is not exactly
// a numeric address is not loopback.
[[nodiscard]] bool is_loopback(std::string_view address);

// Why the server must not start with this address and configuration; empty if
// it may. The rules: the address is a numeric IPv4 or IPv6 address; without
// tokens, authentication must be turned off explicitly; beyond loopback,
// tokens and TLS are both required and turning authentication off is refused.
[[nodiscard]] std::vector<std::string> check_bind(std::string_view address, const Security& s);

}  // namespace ex175
