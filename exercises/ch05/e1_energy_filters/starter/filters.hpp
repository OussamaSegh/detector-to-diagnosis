// SPDX-License-Identifier: MIT
// Exercise 5.1 starter: three energy-window filters.
#pragma once

#include <cstddef>
#include <span>

#include "minidaq/core/single.hpp"

namespace ex {

using minidaq::Single;

// Each copies the singles with lo <= energy <= hi to the front of `out`
// (out.size() >= in.size()), in order, and returns how many. NaN is rejected.
std::size_t filter_branchy(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept;
std::size_t filter_branchless(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept;
std::size_t filter_simd(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept;

}  // namespace ex
