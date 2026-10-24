// SPDX-License-Identifier: MIT
// MiniDAQ - constexpr sine and cosine (Chapter 1).
//
// std::sin and std::cos are not constexpr before C++26 (GCC accepts them as an
// extension, Clang does not), so geometry tables built at compile time need
// their own. Range reduction to [-pi/4, pi/4] plus a short Taylor series gives
// errors below 1e-15 there, which unit tests check against std::sin/std::cos.
#pragma once

#include <cstdint>
#include <numbers>

namespace minidaq::cmath {

namespace detail {
// Taylor series about 0, valid for |x| <= pi/4.
constexpr double sin_poly(double x) noexcept {
  const double x2 = x * x;
  double term = x;
  double sum = x;
  for (int n = 1; n < 12; ++n) {
    term *= -x2 / static_cast<double>((2 * n) * (2 * n + 1));
    sum += term;
  }
  return sum;
}
constexpr double cos_poly(double x) noexcept {
  const double x2 = x * x;
  double term = 1.0;
  double sum = 1.0;
  for (int n = 1; n < 12; ++n) {
    term *= -x2 / static_cast<double>((2 * n - 1) * (2 * n));
    sum += term;
  }
  return sum;
}
}  // namespace detail

// Returns {sin(x), cos(x)}. Intended for |x| up to a few thousand radians.
struct SinCos {
  double sin;
  double cos;
};

constexpr SinCos sincos(double x) noexcept {
  constexpr double half_pi = std::numbers::pi / 2.0;
  // k = nearest integer to x / (pi/2); r = x - k*pi/2 is in [-pi/4, pi/4].
  const double q = x / half_pi;
  const auto k = static_cast<std::int64_t>(q >= 0.0 ? q + 0.5 : q - 0.5);
  const double r = x - static_cast<double>(k) * half_pi;
  const double s = detail::sin_poly(r);
  const double c = detail::cos_poly(r);
  switch (((k % 4) + 4) % 4) {
    case 0: return {s, c};
    case 1: return {c, -s};
    case 2: return {-s, -c};
    default: return {-c, s};
  }
}

constexpr double sin(double x) noexcept { return sincos(x).sin; }
constexpr double cos(double x) noexcept { return sincos(x).cos; }

}  // namespace minidaq::cmath
