#pragma once
// Exercise 2.6 starter: 40 bytes on x86-64. TODO: reorder to fit in 24.
#include <cstdint>

namespace ex {

struct DetectorStatus {
  bool bias_on;
  double singles_rate_hz;
  std::uint16_t block_id;
  float temperature_c;
  bool alarm;
  std::uint32_t bias_mv;
  std::uint8_t fw_revision;
};

}  // namespace ex
