// SPDX-License-Identifier: MIT
// Exercise 32.2: sums of a sliding window over a rate history.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace window {

// The sum of each run of `width` consecutive counts: counts.size() - width + 1 sums, none if
// `width` is 0 or larger than the history.
[[nodiscard]] std::vector<std::int64_t> sums(const std::vector<std::int32_t>& counts,
                                             std::size_t width);

}  // namespace window
