#pragma once
// Exercise 1.5 solution.
#include <array>
#include <cstddef>
#include <numbers>

#include "minidaq/core/constexpr_math.hpp"

namespace ex {

struct Point2 {
  double x;
  double y;
};

// consteval: calling this at run time is a compile error, so the table can
// never be rebuilt by accident on the hot path.
template <std::size_t N>
consteval std::array<Point2, N> make_ring_table(double radius_mm) {
  std::array<Point2, N> t{};
  const double step = 2.0 * std::numbers::pi / static_cast<double>(N);
  for (std::size_t i = 0; i < N; ++i) {
    const auto sc = minidaq::cmath::sincos((static_cast<double>(i) + 0.5) * step);
    t[i] = Point2{radius_mm * sc.cos, radius_mm * sc.sin};
  }
  return t;
}

inline constexpr auto ring384 = make_ring_table<384>(150.0);

}  // namespace ex
