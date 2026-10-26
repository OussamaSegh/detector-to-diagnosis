// SPDX-License-Identifier: MIT
#include "tmp117.hpp"

namespace tmp117 {

std::optional<double> decode_temperature(std::uint8_t msb, std::uint8_t lsb) {
  // TODO: put the bytes together in the right order, read them as a signed 16-bit number, scale
  // it, and refuse the reset value and anything outside the sensor's range.
  (void)msb;
  (void)lsb;
  return std::nullopt;
}

bool is_tmp117(std::uint8_t msb, std::uint8_t lsb) {
  // TODO: compare the device ID bits only.
  (void)msb;
  (void)lsb;
  return false;
}

}  // namespace tmp117
