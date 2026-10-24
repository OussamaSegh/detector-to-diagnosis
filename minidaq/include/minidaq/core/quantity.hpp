// SPDX-License-Identifier: MIT
// MiniDAQ - strong types for physical quantities (Chapter 1).
//
// A Quantity<Tag, Rep> is a number that carries its unit in the type system.
// Picoseconds + KeV does not compile; Picoseconds + Picoseconds does.
// The wrapper is a trivially copyable aggregate of one Rep, so it costs
// nothing at run time (check with Compiler Explorer: same assembly as Rep).
#pragma once

#include <compare>
#include <concepts>
#include <type_traits>

namespace minidaq {

template <typename Tag, typename Rep>
  requires std::is_arithmetic_v<Rep>
class Quantity {
 public:
  using rep = Rep;
  using tag = Tag;

  constexpr Quantity() noexcept = default;
  constexpr explicit Quantity(Rep value) noexcept : value_{value} {}

  [[nodiscard]] constexpr Rep count() const noexcept { return value_; }

  // Same-unit arithmetic only. Scaling by a plain number is allowed,
  // because "twice a time window" is still a time.
  constexpr Quantity& operator+=(Quantity rhs) noexcept {
    value_ += rhs.value_;
    return *this;
  }
  constexpr Quantity& operator-=(Quantity rhs) noexcept {
    value_ -= rhs.value_;
    return *this;
  }

  [[nodiscard]] friend constexpr Quantity operator+(Quantity a, Quantity b) noexcept {
    return Quantity{static_cast<Rep>(a.value_ + b.value_)};
  }
  [[nodiscard]] friend constexpr Quantity operator-(Quantity a, Quantity b) noexcept {
    return Quantity{static_cast<Rep>(a.value_ - b.value_)};
  }
  [[nodiscard]] friend constexpr Quantity operator-(Quantity a) noexcept {
    return Quantity{static_cast<Rep>(-a.value_)};
  }
  [[nodiscard]] friend constexpr Quantity operator*(Quantity a, Rep k) noexcept {
    return Quantity{static_cast<Rep>(a.value_ * k)};
  }
  [[nodiscard]] friend constexpr Quantity operator*(Rep k, Quantity a) noexcept {
    return Quantity{static_cast<Rep>(k * a.value_)};
  }
  [[nodiscard]] friend constexpr Quantity operator/(Quantity a, Rep k) noexcept {
    return Quantity{static_cast<Rep>(a.value_ / k)};
  }
  // Ratio of two quantities of the same unit is a plain number.
  [[nodiscard]] friend constexpr Rep operator/(Quantity a, Quantity b) noexcept {
    return static_cast<Rep>(a.value_ / b.value_);
  }

  friend constexpr auto operator<=>(Quantity, Quantity) noexcept = default;
  friend constexpr bool operator==(Quantity, Quantity) noexcept = default;

 private:
  Rep value_{};
};

// Absolute value for signed quantities (time differences are signed).
template <typename Tag, typename Rep>
[[nodiscard]] constexpr Quantity<Tag, Rep> abs(Quantity<Tag, Rep> q) noexcept {
  return q.count() < Rep{} ? -q : q;
}

}  // namespace minidaq
