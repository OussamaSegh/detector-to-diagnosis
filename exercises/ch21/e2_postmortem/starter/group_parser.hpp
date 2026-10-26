// SPDX-License-Identifier: MIT
// Exercise 21.2: the group parser of a site configuration tool. Groups are braces, nested:
// "{ {a} {b {c}} }" has four groups, nested three deep. Text between braces is ignored here.
#pragma once

#include <cstddef>
#include <string>
#include <string_view>

namespace ex21 {

inline constexpr std::size_t max_depth = 64;  // what the configuration format allows

struct ParseResult {
  bool ok = false;
  std::size_t groups = 0;  // groups in the text
  std::size_t depth = 0;   // deepest nesting
  std::string error;       // why not ok, with the byte offset
};

[[nodiscard]] ParseResult parse_groups(std::string_view text);

}  // namespace ex21
