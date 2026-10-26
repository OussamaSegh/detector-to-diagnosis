// SPDX-License-Identifier: MIT
#include "tmp117.hpp"

namespace tmp117 {

namespace {

constexpr std::uint16_t word(std::uint8_t msb, std::uint8_t lsb) {
  return static_cast<std::uint16_t>((static_cast<unsigned>(msb) << 8U) | lsb);
}

}  // namespace

std::optional<double> decode_temperature(std::uint8_t msb, std::uint8_t lsb) {
  const std::uint16_t raw = word(msb, lsb);
  if (raw == 0x8000) {
    return std::nullopt;  // no conversion has completed since the reset
  }
  // Two's complement of 16 bits; the conversion of an out-of-range value to int16_t is defined
  // (modular) since C++20.
  const double celsius = static_cast<std::int16_t>(raw) / 128.0;
  if (celsius < -55.0 || celsius > 150.0) {
    return std::nullopt;
  }
  return celsius;
}

bool is_tmp117(std::uint8_t msb, std::uint8_t lsb) { return (word(msb, lsb) & 0x0FFFU) == 0x117U; }

}  // namespace tmp117
