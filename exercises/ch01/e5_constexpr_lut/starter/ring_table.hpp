#pragma once
// Exercise 1.5 starter. TODO: fill the table using minidaq::cmath::sincos.
#include <array>
#include <cstddef>

#include "minidaq/core/constexpr_math.hpp"

namespace ex {

struct Point2 {
  double x;
  double y;
};

template <std::size_t N>
consteval std::array<Point2, N> make_ring_table(double radius_mm) {
  std::array<Point2, N> t{};
  (void)radius_mm;  // TODO
  return t;
}

inline constexpr auto ring384 = make_ring_table<384>(150.0);

}  // namespace ex
