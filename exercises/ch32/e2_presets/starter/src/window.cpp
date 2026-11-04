// SPDX-License-Identifier: MIT
#include "window.hpp"

#include <memory>

namespace window {

std::vector<std::int64_t> sums(const std::vector<std::int32_t>& counts, std::size_t width) {
  if (width == 0 || width > counts.size()) {
    return {};
  }
  // A copy in a plain array, as the original code had it for a C interface.
  const std::size_t n = counts.size();
  const auto copy = std::make_unique<std::int32_t[]>(n);
  for (std::size_t i = 0; i < n; ++i) {
    copy[i] = counts[i];
  }
  std::vector<std::int64_t> out;
  std::int64_t s = 0;
  for (std::size_t i = 0; i < width; ++i) {
    s += copy[i];
  }
  out.push_back(s);
  // The defect this exercise's presets must find: the loop runs one step too far and reads
  // copy[n], one past the array. The sum it computes is dropped, so no test sees a wrong value.
  for (std::size_t i = width; i <= n; ++i) {
    s += copy[i] - copy[i - width];
    if (i < n) {
      out.push_back(s);
    }
  }
  return out;
}

}  // namespace window
