#pragma once
// Exercise 2.6 solution: largest alignment first. 8 + 4 + 4 + 2 + 1 + 1 + 1 = 21,
// rounded up to 24 (a multiple of alignof(double) = 8).
#include <cstdint>

namespace ex {

struct DetectorStatus {
  double singles_rate_hz;     // offset 0
  float temperature_c;        // 8
  std::uint32_t bias_mv;      // 12
  std::uint16_t block_id;     // 16
  std::uint8_t fw_revision;   // 18
  bool bias_on;               // 19
  bool alarm;                 // 20, then 3 bytes tail padding
};
static_assert(sizeof(DetectorStatus) == 24);

}  // namespace ex
