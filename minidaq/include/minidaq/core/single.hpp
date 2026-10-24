// SPDX-License-Identifier: MIT
// MiniDAQ - the event types that flow through the pipeline (Chapter 1).
#pragma once

#include <cstdint>
#include <type_traits>

#include "minidaq/core/ids.hpp"
#include "minidaq/core/units.hpp"

namespace minidaq {

// One detected photon: which crystal, when, and how much energy.
// Field order puts the 8-byte member first so the struct has no padding.
struct Single {
  Picoseconds time{};
  CrystalId crystal{};
  KeV energy{};

  friend constexpr bool operator==(const Single&, const Single&) noexcept = default;
};

static_assert(sizeof(Single) == 16, "Single must stay 16 bytes (4 per cache line)");
static_assert(std::is_trivially_copyable_v<Single>);
static_assert(std::is_standard_layout_v<Single>);

enum class CoincidenceKind : std::uint8_t {
  prompt = 0,   // both singles inside the prompt window
  delayed = 1,  // second single from the delayed window (randoms estimate)
};

// A pair of singles accepted by the coincidence sorter. `first` is always the
// earlier single, so time_difference() is >= 0 for prompts.
struct Coincidence {
  Single first{};
  Single second{};
  CoincidenceKind kind{CoincidenceKind::prompt};

  [[nodiscard]] constexpr Picoseconds time_difference() const noexcept {
    return second.time - first.time;
  }
  friend constexpr bool operator==(const Coincidence&, const Coincidence&) noexcept = default;
};

static_assert(std::is_trivially_copyable_v<Coincidence>);

}  // namespace minidaq
