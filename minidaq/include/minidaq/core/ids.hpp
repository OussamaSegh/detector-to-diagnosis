// SPDX-License-Identifier: MIT
// MiniDAQ - identifier types (Chapter 1).
//
// An id is not a number: adding two crystal ids is meaningless, so StrongId
// supports only comparison, hashing and explicit access to the raw value.
#pragma once

#include <compare>
#include <cstdint>
#include <functional>

namespace minidaq {

template <typename Tag, typename Rep = std::uint32_t>
class StrongId {
 public:
  using rep = Rep;
  constexpr StrongId() noexcept = default;
  constexpr explicit StrongId(Rep v) noexcept : value_{v} {}
  [[nodiscard]] constexpr Rep value() const noexcept { return value_; }
  friend constexpr auto operator<=>(StrongId, StrongId) noexcept = default;
  friend constexpr bool operator==(StrongId, StrongId) noexcept = default;

 private:
  Rep value_{};
};

struct CrystalTag {};
struct BoardTag {};

using CrystalId = StrongId<CrystalTag, std::uint32_t>;
using BoardId = StrongId<BoardTag, std::uint16_t>;

}  // namespace minidaq

template <typename Tag, typename Rep>
struct std::hash<minidaq::StrongId<Tag, Rep>> {
  [[nodiscard]] std::size_t operator()(minidaq::StrongId<Tag, Rep> id) const noexcept {
    return std::hash<Rep>{}(id.value());
  }
};
