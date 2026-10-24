#pragma once
// Exercise 2.4 solution: the MDQ-P1 layout. See DESIGN.md.
//  63..49 crystal (15) | 48..38 energy (11) | 37..10 coarse (28) | 9..0 fine (10)
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

struct Fields {
  std::uint32_t crystal;
  std::uint32_t energy_code;
  std::uint64_t coarse;
  std::uint32_t fine;
};

inline constexpr unsigned kFineBits = 10;
inline constexpr unsigned kCoarseBits = 28;
inline constexpr unsigned kEnergyBits = 11;
inline constexpr unsigned kCrystalBits = 15;
static_assert(kFineBits + kCoarseBits + kEnergyBits + kCrystalBits == 64);

inline constexpr std::uint32_t kCrystalMax = (1U << kCrystalBits) - 1;
inline constexpr std::uint32_t kEnergyMax = (1U << kEnergyBits) - 1;
inline constexpr std::uint64_t kCoarseMax = (std::uint64_t{1} << kCoarseBits) - 1;
inline constexpr std::uint32_t kFineMax = (1U << kFineBits) - 1;
inline constexpr std::int64_t kTimeLsbPs = 5;                                  // fine bin
inline constexpr std::int64_t kCoarseTickPs = kTimeLsbPs << kFineBits;        // 5.12 ns
inline constexpr std::int64_t kWrapPeriodPs = kCoarseTickPs << kCoarseBits;   // 1.374 s
inline constexpr float kEnergyLsbKeV = 0.5F;
inline constexpr float kEnergyMaxKeV = static_cast<float>(kEnergyMax) * kEnergyLsbKeV;

constexpr std::uint64_t pack(Fields f) {
  return (std::uint64_t{f.crystal & kCrystalMax} << (kEnergyBits + kCoarseBits + kFineBits)) |
         (std::uint64_t{f.energy_code & kEnergyMax} << (kCoarseBits + kFineBits)) |
         ((f.coarse & kCoarseMax) << kFineBits) | std::uint64_t{f.fine & kFineMax};
}

constexpr Fields unpack(std::uint64_t w) {
  return Fields{static_cast<std::uint32_t>(w >> (kEnergyBits + kCoarseBits + kFineBits)) & kCrystalMax,
                static_cast<std::uint32_t>(w >> (kCoarseBits + kFineBits)) & kEnergyMax,
                (w >> kFineBits) & kCoarseMax, static_cast<std::uint32_t>(w) & kFineMax};
}

inline std::uint64_t encode(const Single& s) {
  const std::int64_t t = s.time_ps % kWrapPeriodPs;  // precondition: time_ps >= 0
  const auto lsb = static_cast<std::uint64_t>(t / kTimeLsbPs);
  std::uint32_t e = 0;
  if (s.energy_kev >= kEnergyMaxKeV) {
    e = kEnergyMax;
  } else if (s.energy_kev > 0.0F) {
    e = static_cast<std::uint32_t>(std::lround(s.energy_kev / kEnergyLsbKeV));
  }
  return pack(Fields{s.crystal, e, lsb >> kFineBits, static_cast<std::uint32_t>(lsb & kFineMax)});
}

inline Single decode(std::uint64_t w) {
  const Fields f = unpack(w);
  const auto t = static_cast<std::int64_t>(f.coarse) * kCoarseTickPs + static_cast<std::int64_t>(f.fine) * kTimeLsbPs;
  return Single{t, f.crystal, static_cast<float>(f.energy_code) * kEnergyLsbKeV};
}

// Shifts are defined on values, not on memory, so this is correct on any host.
inline std::array<std::byte, 8> to_bytes(std::uint64_t w) {
  std::array<std::byte, 8> b{};
  for (std::size_t i = 0; i < 8; ++i) {
    b[i] = static_cast<std::byte>((w >> (8 * i)) & 0xFFU);
  }
  return b;
}

inline std::uint64_t from_bytes(const std::array<std::byte, 8>& b) {
  std::uint64_t w = 0;
  for (std::size_t i = 0; i < 8; ++i) {
    w |= std::uint64_t{std::to_integer<std::uint8_t>(b[i])} << (8 * i);
  }
  return w;
}

}  // namespace ex
