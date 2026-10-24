// SPDX-License-Identifier: MIT
// MiniDAQ - minidaq::Expected<T, E>, a small std::expected (Chapter 1).
//
// Why this file exists: std::expected is C++23. GCC 13 ships it in -std=c++23
// mode, but Clang 17/18 used together with libstdc++ 13 do not expose it
// (libstdc++ gates <expected> on __cpp_concepts >= 202002L, which those Clang
// versions do not define). MiniDAQ must build with both compilers in C++20, so
// we provide the subset we use. When the standard library has std::expected
// (feature-test macro __cpp_lib_expected), the names below are aliases for the
// standard ones, so code written against this header is also valid C++23.
#pragma once

#include <version>

#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202202L
#include <expected>

namespace minidaq {
template <typename T, typename E>
using Expected = std::expected<T, E>;
template <typename E>
using Unexpected = std::unexpected<E>;
}  // namespace minidaq

#else

#include <cstdlib>
#include <memory>
#include <type_traits>
#include <utility>

namespace minidaq {

template <typename E>
class Unexpected {
 public:
  constexpr explicit Unexpected(E e) noexcept(std::is_nothrow_move_constructible_v<E>)
      : error_{std::move(e)} {}
  [[nodiscard]] constexpr const E& error() const& noexcept { return error_; }
  [[nodiscard]] constexpr E& error() & noexcept { return error_; }
  [[nodiscard]] constexpr E&& error() && noexcept { return std::move(error_); }

 private:
  E error_;
};

template <typename E>
Unexpected(E) -> Unexpected<E>;

// Value-or-error. Unlike std::expected, accessing the wrong alternative
// aborts instead of throwing: MiniDAQ hot-path code is built to run without
// exceptions, and reading the value of a failed parse is always a bug.
template <typename T, typename E>
class Expected {
  static_assert(!std::is_reference_v<T> && !std::is_reference_v<E>);
  static_assert(std::is_nothrow_destructible_v<T> && std::is_nothrow_destructible_v<E>);

 public:
  using value_type = T;
  using error_type = E;

  constexpr Expected() requires std::is_default_constructible_v<T> : has_value_{true} {
    std::construct_at(&value_);
  }
  // NOLINTNEXTLINE(google-explicit-constructor): implicit like std::expected
  constexpr Expected(const T& v) : has_value_{true} { std::construct_at(&value_, v); }
  // NOLINTNEXTLINE(google-explicit-constructor)
  constexpr Expected(T&& v) : has_value_{true} { std::construct_at(&value_, std::move(v)); }
  // NOLINTNEXTLINE(google-explicit-constructor)
  constexpr Expected(Unexpected<E> u) : has_value_{false} {
    std::construct_at(&error_, std::move(u).error());
  }

  constexpr Expected(const Expected& other) : has_value_{other.has_value_} {
    if (has_value_) {
      std::construct_at(&value_, other.value_);
    } else {
      std::construct_at(&error_, other.error_);
    }
  }
  constexpr Expected(Expected&& other) noexcept(std::is_nothrow_move_constructible_v<T> &&
                                                std::is_nothrow_move_constructible_v<E>)
      : has_value_{other.has_value_} {
    if (has_value_) {
      std::construct_at(&value_, std::move(other.value_));
    } else {
      std::construct_at(&error_, std::move(other.error_));
    }
  }
  constexpr Expected& operator=(const Expected& other) {
    if (this != &other) {
      destroy();
      has_value_ = other.has_value_;
      if (has_value_) {
        std::construct_at(&value_, other.value_);
      } else {
        std::construct_at(&error_, other.error_);
      }
    }
    return *this;
  }
  constexpr Expected& operator=(Expected&& other) noexcept(
      std::is_nothrow_move_constructible_v<T> && std::is_nothrow_move_constructible_v<E>) {
    if (this != &other) {
      destroy();
      has_value_ = other.has_value_;
      if (has_value_) {
        std::construct_at(&value_, std::move(other.value_));
      } else {
        std::construct_at(&error_, std::move(other.error_));
      }
    }
    return *this;
  }
  constexpr ~Expected() { destroy(); }

  [[nodiscard]] constexpr bool has_value() const noexcept { return has_value_; }
  [[nodiscard]] constexpr explicit operator bool() const noexcept { return has_value_; }

  [[nodiscard]] constexpr T& value() & { check(has_value_); return value_; }
  [[nodiscard]] constexpr const T& value() const& { check(has_value_); return value_; }
  [[nodiscard]] constexpr T&& value() && { check(has_value_); return std::move(value_); }
  [[nodiscard]] constexpr T& operator*() & { return value(); }
  [[nodiscard]] constexpr const T& operator*() const& { return value(); }
  [[nodiscard]] constexpr T* operator->() { return &value(); }
  [[nodiscard]] constexpr const T* operator->() const { return &value(); }

  [[nodiscard]] constexpr const E& error() const& { check(!has_value_); return error_; }
  [[nodiscard]] constexpr E& error() & { check(!has_value_); return error_; }

  template <typename U>
  [[nodiscard]] constexpr T value_or(U&& fallback) const& {
    return has_value_ ? value_ : static_cast<T>(std::forward<U>(fallback));
  }

  // Monadic helpers (the subset MiniDAQ uses).
  template <typename F>
  constexpr auto and_then(F&& f) const& {
    using R = std::remove_cvref_t<std::invoke_result_t<F, const T&>>;
    if (has_value_) {
      return std::forward<F>(f)(value_);
    }
    return R{Unexpected<E>{error_}};
  }
  template <typename F>
  constexpr auto transform(F&& f) const& {
    using U = std::remove_cvref_t<std::invoke_result_t<F, const T&>>;
    if (has_value_) {
      return Expected<U, E>{std::forward<F>(f)(value_)};
    }
    return Expected<U, E>{Unexpected<E>{error_}};
  }

 private:
  static constexpr void check(bool ok) {
    if (!ok) {
      std::abort();
    }
  }
  constexpr void destroy() noexcept {
    if (has_value_) {
      std::destroy_at(&value_);
    } else {
      std::destroy_at(&error_);
    }
  }

  union {
    T value_;
    E error_;
  };
  bool has_value_;
};

// Expected<void, E>: success carries no value (for example a write).
template <typename E>
class Expected<void, E> {
 public:
  using value_type = void;
  using error_type = E;
  constexpr Expected() noexcept = default;
  // NOLINTNEXTLINE(google-explicit-constructor)
  constexpr Expected(Unexpected<E> u) : error_{std::move(u).error()}, has_value_{false} {}
  [[nodiscard]] constexpr bool has_value() const noexcept { return has_value_; }
  [[nodiscard]] constexpr explicit operator bool() const noexcept { return has_value_; }
  constexpr void value() const {
    if (!has_value_) {
      std::abort();
    }
  }
  [[nodiscard]] constexpr const E& error() const {
    if (has_value_) {
      std::abort();
    }
    return error_;
  }

 private:
  E error_{};
  bool has_value_{true};
};

}  // namespace minidaq

#endif
