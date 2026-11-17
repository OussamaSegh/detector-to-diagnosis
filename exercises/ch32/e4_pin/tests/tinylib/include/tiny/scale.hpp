// SPDX-License-Identifier: MIT
// tinylib 1.0. Third-party code, reviewed as SOUP: it narrows a double to an int on purpose,
// which -Wconversion reports in every file that includes it.
#pragma once

namespace tiny {

inline int scaled(double value, double gain) {
  int result = value * gain;
  return result;
}

}  // namespace tiny
