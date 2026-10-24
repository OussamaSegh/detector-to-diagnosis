// SPDX-License-Identifier: MIT
// MiniDAQ - strict number parsing for command lines and text files (Chapter 7).
//
// std::atoi("7OO") is 7, std::atoi("abc") is 0 and std::atoi("99999") stored
// in a std::uint16_t is 34463: none of them reports an error (CERT ERR34-C).
// parse_number accepts a value only if the whole text is a number of type T
// within [lo, hi]; anything else is std::nullopt, which the caller reports.
#pragma once

#include <charconv>
#include <cmath>
#include <limits>
#include <optional>
#include <string_view>
#include <system_error>
#include <type_traits>

namespace minidaq {

// [snippet:parse_number]
template <typename T>
  requires std::is_arithmetic_v<T> && (!std::is_same_v<T, bool>)
[[nodiscard]] std::optional<T> parse_number(std::string_view text, T lo = std::numeric_limits<T>::lowest(),
                                            T hi = std::numeric_limits<T>::max()) noexcept {
  T value{};
  const char* const end = text.data() + text.size();
  const auto [ptr, ec] = std::from_chars(text.data(), end, value);
  if (text.empty() || ec != std::errc{} || ptr != end) {
    return std::nullopt;  // empty, not a number, out of T's range, or trailing text
  }
  if constexpr (std::is_floating_point_v<T>) {
    if (!std::isfinite(value)) {
      return std::nullopt;  // from_chars accepts "inf" and "nan"
    }
  }
  if (value < lo || value > hi) {
    return std::nullopt;
  }
  return value;
}
// [/snippet:parse_number]

// For option parsing: stores the value in `out` only if `text` is valid.
template <typename T>
[[nodiscard]] bool parse_into(std::string_view text, T& out, T lo = std::numeric_limits<T>::lowest(),
                              T hi = std::numeric_limits<T>::max()) noexcept {
  const auto v = parse_number<T>(text, lo, hi);
  if (v) {
    out = *v;
  }
  return v.has_value();
}

}  // namespace minidaq
