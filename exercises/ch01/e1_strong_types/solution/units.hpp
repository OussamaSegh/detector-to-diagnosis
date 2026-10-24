#pragma once
// Exercise 1.1 solution: a minimal tagged Quantity. See NOTES.md.
#include <compare>
#include <cstdint>
#include <type_traits>

namespace ex {

template <typename Tag, typename Rep>
  requires std::is_arithmetic_v<Rep>
class Quantity {
 public:
  constexpr Quantity() = default;
  constexpr explicit Quantity(Rep v) : v_{v} {}
  [[nodiscard]] constexpr Rep count() const { return v_; }

  friend constexpr Quantity operator+(Quantity a, Quantity b) { return Quantity{static_cast<Rep>(a.v_ + b.v_)}; }
  friend constexpr Quantity operator-(Quantity a, Quantity b) { return Quantity{static_cast<Rep>(a.v_ - b.v_)}; }
  friend constexpr Quantity operator*(Quantity a, Rep k) { return Quantity{static_cast<Rep>(a.v_ * k)}; }
  friend constexpr Quantity operator*(Rep k, Quantity a) { return Quantity{static_cast<Rep>(k * a.v_)}; }
  friend constexpr Rep operator/(Quantity a, Quantity b) { return static_cast<Rep>(a.v_ / b.v_); }
  friend constexpr auto operator<=>(Quantity, Quantity) = default;

 private:
  Rep v_{};
};

struct PicosecondsTag {};
struct KeVTag {};
using Picoseconds = Quantity<PicosecondsTag, std::int64_t>;
using KeV = Quantity<KeVTag, float>;

template <typename Tag, typename Rep>
constexpr Rep count(Quantity<Tag, Rep> q) { return q.count(); }

}  // namespace ex
