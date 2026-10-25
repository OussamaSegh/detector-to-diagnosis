// SPDX-License-Identifier: MIT
// Exercise 17.5 starter: the checks pass for 127.0.0.1 and 0.0.0.0, and the
// tests find the rest. Parse addresses with inet_pton, never by their text.
#include "bind_check.hpp"

namespace ex175 {

bool is_loopback(std::string_view address) {
  // TODO: IPv6, the IPv4-mapped form, and text that only looks like an address.
  return address.starts_with("127.") || address == "localhost" || address == "::1";
}

std::vector<std::string> check_bind(std::string_view address, const Security& s) {
  std::vector<std::string> problems;
  // TODO: refuse what is not a numeric address.
  if (!s.tokens && !s.allow_unauthenticated) {
    problems.emplace_back("no tokens: clients could not authenticate");
  }
  if (!is_loopback(address) && !s.tls) {  // TODO: is TLS enough on its own?
    problems.emplace_back("beyond loopback, TLS is required");
  }
  return problems;
}

}  // namespace ex175
