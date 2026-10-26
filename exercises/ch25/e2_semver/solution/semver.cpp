// SPDX-License-Identifier: MIT
#include "semver.hpp"

#include <algorithm>
#include <charconv>
#include <system_error>
#include <tuple>

namespace semver {

namespace {

bool is_digits(std::string_view s) {
  return !s.empty() && std::ranges::all_of(s, [](char c) { return c >= '0' && c <= '9'; });
}

bool is_identifier(std::string_view s) {
  return !s.empty() && std::ranges::all_of(s, [](char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '-';
  });
}

// A number without a leading zero, as the three version numbers and numeric identifiers are.
std::optional<std::uint64_t> number(std::string_view s) {
  if (!is_digits(s) || (s.size() > 1 && s.front() == '0')) {
    return std::nullopt;
  }
  std::uint64_t v = 0;
  const auto [end, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
  if (ec != std::errc{} || end != s.data() + s.size()) {
    return std::nullopt;
  }
  return v;
}

std::optional<std::vector<std::string>> identifiers(std::string_view s, bool numeric_rule) {
  std::vector<std::string> out;
  while (true) {
    const auto dot = s.find('.');
    const std::string_view id = s.substr(0, dot);
    if (!is_identifier(id) || (numeric_rule && is_digits(id) && !number(id))) {
      return std::nullopt;
    }
    out.emplace_back(id);
    if (dot == std::string_view::npos) {
      return out;
    }
    s.remove_prefix(dot + 1);
  }
}

std::strong_ordering compare_identifier(const std::string& a, const std::string& b) {
  const bool an = is_digits(a);
  const bool bn = is_digits(b);
  if (an && bn) {
    // No leading zeros, so the longer number is the larger, and equal lengths compare as text.
    return a.size() != b.size() ? a.size() <=> b.size() : a <=> b;
  }
  if (an != bn) {
    return an ? std::strong_ordering::less : std::strong_ordering::greater;
  }
  return a <=> b;
}

}  // namespace

std::optional<Version> parse(std::string_view text) {
  Version v;
  if (const auto plus = text.find('+'); plus != std::string_view::npos) {
    const auto build = identifiers(text.substr(plus + 1), false);
    if (!build) {
      return std::nullopt;
    }
    v.build = std::string{text.substr(plus + 1)};
    text = text.substr(0, plus);
  }
  if (const auto dash = text.find('-'); dash != std::string_view::npos) {
    auto pre = identifiers(text.substr(dash + 1), true);
    if (!pre) {
      return std::nullopt;
    }
    v.pre = std::move(*pre);
    text = text.substr(0, dash);
  }
  for (std::uint64_t* part : {&v.major, &v.minor, &v.patch}) {
    const auto dot = text.find('.');
    const bool last = part == &v.patch;
    if ((dot == std::string_view::npos) != last) {
      return std::nullopt;  // fewer or more than three numbers
    }
    const auto n = number(text.substr(0, dot));
    if (!n) {
      return std::nullopt;
    }
    *part = *n;
    text = last ? std::string_view{} : text.substr(dot + 1);
  }
  return v;
}

std::strong_ordering compare(const Version& a, const Version& b) {
  if (const auto c = std::tie(a.major, a.minor, a.patch) <=> std::tie(b.major, b.minor, b.patch);
      c != 0) {
    return c;
  }
  if (a.pre.empty() || b.pre.empty()) {
    return a.pre.empty() <=> b.pre.empty();  // a release is higher than any of its pre-releases
  }
  const std::size_t n = std::min(a.pre.size(), b.pre.size());
  for (std::size_t i = 0; i < n; ++i) {
    if (const auto c = compare_identifier(a.pre[i], b.pre[i]); c != 0) {
      return c;
    }
  }
  return a.pre.size() <=> b.pre.size();
}

}  // namespace semver
