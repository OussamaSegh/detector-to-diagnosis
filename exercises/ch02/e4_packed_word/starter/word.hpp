#pragma once
// Exercise 2.4 starter. TODO: choose the bit layout and implement every function.
#include <array>
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

// TODO: set these from your layout (they must add up to 64 bits).
inline constexpr std::uint32_t kCrystalMax = 0;
inline constexpr std::uint32_t kEnergyMax = 0;
inline constexpr std::uint64_t kCoarseMax = 0;
inline constexpr std::uint32_t kFineMax = 0;
inline constexpr std::int64_t kTimeLsbPs = 1;
inline constexpr std::int64_t kWrapPeriodPs = 1;
inline constexpr float kEnergyLsbKeV = 1.0F;
inline constexpr float kEnergyMaxKeV = 0.0F;

constexpr std::uint64_t pack(Fields) { return 0; }                // TODO
constexpr Fields unpack(std::uint64_t) { return {}; }             // TODO
inline std::uint64_t encode(const Single&) { return 0; }          // TODO
inline Single decode(std::uint64_t) { return {}; }                // TODO
inline std::array<std::byte, 8> to_bytes(std::uint64_t) { return {}; }  // TODO
inline std::uint64_t from_bytes(const std::array<std::byte, 8>&) { return 0; }  // TODO

}  // namespace ex
