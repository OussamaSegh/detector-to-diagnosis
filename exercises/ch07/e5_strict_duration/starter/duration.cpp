// SPDX-License-Identifier: MIT
#include "duration.hpp"

#include <cstdlib>
#include <string>

namespace ex75 {

// TODO: the "obvious" version below accepts far too much. Replace it.
std::optional<std::chrono::nanoseconds> parse_duration(std::string_view text) noexcept {
  const std::string s{text};
  char* end = nullptr;
  const double v = std::strtod(s.c_str(), &end);
  const std::string_view unit{end};
  double scale = 1.0;
  if (unit == "us") {
    scale = 1e3;
  } else if (unit == "ms") {
    scale = 1e6;
  } else if (unit == "s") {
    scale = 1e9;
  } else if (unit == "min") {
    scale = 60e9;
  }
  return std::chrono::nanoseconds{static_cast<long long>(v * scale)};
}

}  // namespace ex75
