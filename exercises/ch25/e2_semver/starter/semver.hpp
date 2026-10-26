// SPDX-License-Identifier: MIT
// Exercise 25.2: version precedence as Semantic Versioning 2.0.0 defines it (semver.org, section
// 11), which decides whether an update is newer than what is installed.
#pragma once

#include <compare>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace semver {

struct Version {
  std::uint64_t major = 0;
  std::uint64_t minor = 0;
  std::uint64_t patch = 0;
  std::vector<std::string> pre;  // the dot-separated identifiers after '-'; empty: a release
  std::string build;             // after '+'; kept, but never part of the precedence
};

// Parses MAJOR.MINOR.PATCH[-PRE][+BUILD]:
// - the three numbers are digits only, without a leading zero (0 itself is fine);
// - PRE and BUILD are non-empty dot-separated identifiers of [0-9A-Za-z-], none empty;
// - a numeric identifier in PRE (digits only) has no leading zero.
// Empty for anything else, including a number too large for 64 bits.
[[nodiscard]] std::optional<Version> parse(std::string_view text);

// Precedence: the numbers in order; then a pre-release is lower than its release; then the
// identifiers of two pre-releases from left to right: numeric ones by value, others by ASCII
// order, a numeric one lower than a non-numeric one; when all compared identifiers are equal,
// the one with fewer identifiers is lower. Build metadata does not count: 1.0.0+a == 1.0.0+b.
[[nodiscard]] std::strong_ordering compare(const Version& a, const Version& b);

}  // namespace semver
