// SPDX-License-Identifier: MIT
#include "minidaq/format/raw_single.hpp"

#include <bit>
#include <cmath>
#include <cstdint>
#include <cstring>

#include "minidaq/core/bits.hpp"
#include "minidaq/core/geometry.hpp"

namespace minidaq {

std::string_view to_string(ParseError e) noexcept {
  switch (e) {
    case ParseError::truncated: return "truncated";
    case ParseError::negative_time: return "negative_time";
    case ParseError::crystal_out_of_range: return "crystal_out_of_range";
    case ParseError::energy_not_finite: return "energy_not_finite";
    case ParseError::energy_out_of_range: return "energy_out_of_range";
  }
  return "unknown";
}

namespace {
template <typename T>
T load_le(const std::byte* p) noexcept {
  T v;
  std::memcpy(&v, p, sizeof v);  // memcpy: no alignment or aliasing UB
  return from_little_endian(v);
}
template <typename T>
void store_le(std::byte* p, T v) noexcept {
  v = to_little_endian(v);
  std::memcpy(p, &v, sizeof v);
}
}  // namespace

// [snippet:parse]
Expected<Single, ParseError> parse_single(std::span<const std::byte> bytes) noexcept {
  if (bytes.size() < raw16_size) {
    return Unexpected{ParseError::truncated};
  }
  const auto time = load_le<std::int64_t>(bytes.data());
  const auto crystal = load_le<std::uint32_t>(bytes.data() + 8);
  const auto energy = std::bit_cast<float>(load_le<std::uint32_t>(bytes.data() + 12));

  if (time < 0) {
    return Unexpected{ParseError::negative_time};
  }
  if (crystal >= ScannerGeometry::num_crystals) {
    return Unexpected{ParseError::crystal_out_of_range};
  }
  if (!std::isfinite(energy)) {
    return Unexpected{ParseError::energy_not_finite};
  }
  if (energy < 0.0F || energy > raw16_max_energy_kev) {
    return Unexpected{ParseError::energy_out_of_range};
  }
  return Single{Picoseconds{time}, CrystalId{crystal}, KeV{energy}};
}
// [/snippet:parse]

std::array<std::byte, raw16_size> serialize_raw16(const Single& s) noexcept {
  std::array<std::byte, raw16_size> out{};
  store_le<std::int64_t>(out.data(), s.time.count());
  store_le<std::uint32_t>(out.data() + 8, s.crystal.value());
  store_le<std::uint32_t>(out.data() + 12, std::bit_cast<std::uint32_t>(s.energy.count()));
  return out;
}

}  // namespace minidaq
