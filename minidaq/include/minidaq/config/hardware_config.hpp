// SPDX-License-Identifier: MIT
// MiniDAQ - the description of the front-end hardware: which boards, behind which bus, and the
// settings of their slow control (Chapter 22). A JSON file that minidaq_server reads at start-up
// with --hardware, parsed as strictly as the acquisition configuration (Chapter 6).
//
//   {"schema_version": "1.0", "backend": "simulated",
//    "boards": [{"slot": 0}, {"slot": 1, "temperature_c": 31.5}],
//    "bias": {"ramp_v_per_s": 5.0}, "temperature": {"alarm_c": 40.0}}
//
// backend "mmio": each board is a register window of a device file, a UIO device or a PCI
// resource file: {"device": "/dev/uio0", "offset": 0, "size": 4096}. backend "simulated": each
// board is a hw::FakeBoard, whose temperature, dark current and fault the file sets, and whose
// temperature can follow a file (temperature_file) that a test or a demonstration rewrites.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/hw/slow_control.hpp"

namespace minidaq::config {

inline constexpr int hardware_supported_major = 1;
inline constexpr int hardware_supported_minor = 0;
inline constexpr std::size_t max_boards = 64;

struct BoardConfig {
  // mmio
  std::string device;
  std::uint64_t offset = 0;  // a multiple of the page size
  std::uint64_t size = 4096;
  // simulated
  std::uint32_t slot = 0;
  double temperature_c = 25.0;
  std::string temperature_file;  // empty: the temperature stays temperature_c
  double dark_current_ua = 2.0;
  std::string fault = "none";  // "none", "unresponsive", "vanished", "weak_supply"
};

struct HardwareConfig {
  std::string backend = "simulated";  // "simulated" or "mmio"
  std::vector<BoardConfig> boards;
  hw::SlowControlSettings settings;
};

[[nodiscard]] Expected<HardwareConfig, ConfigErrors> parse_hardware_config(
    std::string_view json_text);

}  // namespace minidaq::config
