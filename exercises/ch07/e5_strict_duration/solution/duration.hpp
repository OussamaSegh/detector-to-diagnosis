// SPDX-License-Identifier: MIT
// Exercise 7.5: parse a duration such as "250ms" from a configuration file,
// strictly. The grammar: digits, optionally a '.' and more digits, then
// immediately one of the units ns, us, ms, s, min. No sign, no exponent, no
// spaces. The result must be a whole number of nanoseconds that fits in
// std::chrono::nanoseconds; anything else is std::nullopt.
#pragma once

#include <chrono>
#include <optional>
#include <string_view>

namespace ex75 {

[[nodiscard]] std::optional<std::chrono::nanoseconds> parse_duration(std::string_view text) noexcept;

}  // namespace ex75
