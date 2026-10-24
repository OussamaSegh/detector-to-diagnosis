// SPDX-License-Identifier: MIT
// Exercise 5.1 starter.
#include "filters.hpp"

namespace ex {

std::size_t filter_branchy(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
  // TODO: if (inside) out[k++] = s;
  (void)in, (void)out, (void)lo, (void)hi;
  return 0;
}

std::size_t filter_branchless(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
  // TODO: write every single, advance k only when it is inside.
  (void)in, (void)out, (void)lo, (void)hi;
  return 0;
}

std::size_t filter_simd(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
  // TODO: intrinsics with a target attribute and a run-time CPU check, or std::experimental::simd.
  (void)in, (void)out, (void)lo, (void)hi;
  return 0;
}

}  // namespace ex
