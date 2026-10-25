// SPDX-License-Identifier: MIT
#include "bind_check.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>

#include <algorithm>
#include <array>
#include <cstdint>

namespace ex175 {

namespace {

enum class Kind { invalid, v4, v6 };

// inet_pton accepts exactly the numeric forms and needs a NUL-terminated copy.
Kind parse(std::string_view address, in_addr& v4, in6_addr& v6) {
  const std::string s{address};
  if (s.size() != address.size() || s.find('\0') != std::string::npos) {
    return Kind::invalid;
  }
  if (::inet_pton(AF_INET, s.c_str(), &v4) == 1) {
    return Kind::v4;
  }
  if (::inet_pton(AF_INET6, s.c_str(), &v6) == 1) {
    return Kind::v6;
  }
  return Kind::invalid;
}

bool v4_loopback(std::uint32_t network_order) { return (ntohl(network_order) >> 24U) == 127U; }

}  // namespace

// [snippet:loopback]
bool is_loopback(std::string_view address) {
  in_addr v4{};
  in6_addr v6{};
  switch (parse(address, v4, v6)) {
    case Kind::v4:
      return v4_loopback(v4.s_addr);
    case Kind::v6: {
      const unsigned char* b = v6.s6_addr;
      static constexpr std::array<unsigned char, 16> one{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1};
      static constexpr std::array<unsigned char, 12> mapped{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xff, 0xff};
      if (std::equal(one.begin(), one.end(), b)) {
        return true;
      }
      return std::equal(mapped.begin(), mapped.end(), b) && b[12] == 127;  // the IPv4 part, in network order
    }
    case Kind::invalid:
      break;
  }
  return false;
}
// [/snippet:loopback]

std::vector<std::string> check_bind(std::string_view address, const Security& s) {
  in_addr v4{};
  in6_addr v6{};
  if (parse(address, v4, v6) == Kind::invalid) {
    return {"'" + std::string{address} + "' is not a numeric IPv4 or IPv6 address"};
  }
  std::vector<std::string> problems;
  if (!s.tokens && !s.allow_unauthenticated) {
    problems.emplace_back("no tokens: clients could not authenticate (turn authentication off explicitly)");
  }
  if (!is_loopback(address)) {
    if (!s.tokens || s.allow_unauthenticated) {
      problems.emplace_back("beyond loopback, clients must authenticate with tokens");
    }
    if (!s.tls) {
      problems.emplace_back("beyond loopback, TLS is required");
    }
  }
  return problems;
}

}  // namespace ex175
