// SPDX-License-Identifier: MIT
// Exercise 22.3: the registers of a TMP117 temperature sensor.
#pragma once

#include <cstdint>
#include <optional>

namespace tmp117 {

inline constexpr std::uint8_t temp_result = 0x00;
inline constexpr std::uint8_t configuration = 0x01;
inline constexpr std::uint8_t device_id = 0x0F;

// The temperature in degrees Celsius of a temperature result register, read over I2C as two
// bytes, the most significant first. Empty for a value that is not a temperature: the reset value
// 0x8000, which the sensor holds until its first conversion, and anything outside -55 to 150 C.
[[nodiscard]] std::optional<double> decode_temperature(std::uint8_t msb, std::uint8_t lsb);

// Whether a device ID register, read like the result register, identifies a TMP117 (device ID
// 0x117 in bits 11 to 0), whatever the revision in bits 15 to 12.
[[nodiscard]] bool is_tmp117(std::uint8_t msb, std::uint8_t lsb);

}  // namespace tmp117
