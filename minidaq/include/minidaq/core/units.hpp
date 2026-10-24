// SPDX-License-Identifier: MIT
// MiniDAQ - the units used throughout the acquisition chain (Chapter 1).
#pragma once

#include <cstdint>

#include "minidaq/core/quantity.hpp"

namespace minidaq {

struct PicosecondsTag {};
struct KeVTag {};

// Time is an integer count of picoseconds. 2^63 ps is about 106 days, far
// longer than any acquisition, and integer time never loses precision the way
// a double does once the value exceeds 2^53 ps (about 2.5 hours).
using Picoseconds = Quantity<PicosecondsTag, std::int64_t>;

// Energy in keV. float is enough: detector energy resolution is around 10%,
// and float keeps a Single at 16 bytes.
using KeV = Quantity<KeVTag, float>;

namespace literals {
[[nodiscard]] consteval Picoseconds operator""_ps(unsigned long long v) {
  return Picoseconds{static_cast<std::int64_t>(v)};
}
[[nodiscard]] consteval Picoseconds operator""_ns(unsigned long long v) {
  return Picoseconds{static_cast<std::int64_t>(v * 1'000ULL)};
}
[[nodiscard]] consteval Picoseconds operator""_us(unsigned long long v) {
  return Picoseconds{static_cast<std::int64_t>(v * 1'000'000ULL)};
}
[[nodiscard]] consteval Picoseconds operator""_ms(unsigned long long v) {
  return Picoseconds{static_cast<std::int64_t>(v * 1'000'000'000ULL)};
}
[[nodiscard]] consteval KeV operator""_keV(long double v) { return KeV{static_cast<float>(v)}; }
[[nodiscard]] consteval KeV operator""_keV(unsigned long long v) { return KeV{static_cast<float>(v)}; }
}  // namespace literals

}  // namespace minidaq
