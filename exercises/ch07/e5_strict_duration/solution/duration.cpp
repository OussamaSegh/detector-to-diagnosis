// SPDX-License-Identifier: MIT
#include "duration.hpp"

#include <array>
#include <cstdint>
#include <limits>
#include <utility>

namespace ex75 {
namespace {

struct Unit {
  std::string_view suffix;
  std::int64_t ns;
};
// The suffix must equal one of these exactly, so their order does not matter.
constexpr std::array<Unit, 5> units{{{"ns", 1}, {"us", 1'000}, {"ms", 1'000'000}, {"s", 1'000'000'000},
                                     {"min", 60'000'000'000}}};

constexpr bool is_digit(char c) noexcept { return c >= '0' && c <= '9'; }

}  // namespace

// [snippet:parse]
std::optional<std::chrono::nanoseconds> parse_duration(std::string_view text) noexcept {
  // Split into integer digits, fraction digits and unit; all integer arithmetic,
  // so "0.1s" is exactly 100'000'000 ns (no binary floating-point rounding).
  std::size_t i = 0;
  while (i < text.size() && is_digit(text[i])) {
    ++i;
  }
  const std::string_view whole = text.substr(0, i);
  std::string_view frac;
  if (i < text.size() && text[i] == '.') {
    const std::size_t start = ++i;
    while (i < text.size() && is_digit(text[i])) {
      ++i;
    }
    frac = text.substr(start, i - start);
    if (frac.empty()) {
      return std::nullopt;  // "1.s"
    }
  }
  if (whole.empty()) {
    return std::nullopt;  // ".5s", "s", "-1s", ""
  }
  const std::string_view suffix = text.substr(i);
  const Unit* unit = nullptr;
  for (const Unit& u : units) {
    if (u.suffix == suffix) {
      unit = &u;
    }
  }
  if (unit == nullptr) {
    return std::nullopt;  // no unit, unknown unit, or anything after it
  }
  constexpr std::int64_t max = std::numeric_limits<std::int64_t>::max();
  std::int64_t ns = 0;
  for (const char c : whole) {  // ns = ns * 10 + digit, refusing to overflow
    if (ns > (max - (c - '0')) / 10) {
      return std::nullopt;
    }
    ns = ns * 10 + (c - '0');
  }
  if (ns > max / unit->ns) {
    return std::nullopt;
  }
  ns *= unit->ns;
  // The fraction: each digit is worth unit/10, unit/100, ... nanoseconds; a digit
  // whose place is below one nanosecond must be 0, or the value is not whole.
  std::int64_t place = unit->ns;
  for (const char c : frac) {
    const std::int64_t digit = c - '0';
    if (place % 10 != 0) {
      if (digit != 0) {
        return std::nullopt;  // "1.5ns": half a nanosecond
      }
      continue;
    }
    place /= 10;
    if (ns > max - digit * place) {
      return std::nullopt;
    }
    ns += digit * place;
  }
  return std::chrono::nanoseconds{ns};
}
// [/snippet:parse]

}  // namespace ex75
