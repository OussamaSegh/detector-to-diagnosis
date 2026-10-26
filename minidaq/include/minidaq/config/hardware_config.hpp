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
//
// Schema 1.1 (Chapter 24) adds, for simulated boards, the firmware version the board reports,
// the rates of its output FIFO and the faults "stalled_link" and "hung_bus" (Chapter 25: a bus
// access that does not return for a minute); and for every backend the time the
// boards may take to switch their triggers on and to send what they hold at the end of a run:
//   "run": {"trigger_timeout_ms": 2000, "drain_timeout_ms": 2000}
// The firmware versions the software supports are not in the file: they are a property of the
// software, recorded in the interface control document, and no description can widen them.
#pragma once

#include <chrono>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/hw/slow_control.hpp"

namespace minidaq::config {

inline constexpr int hardware_supported_major = 1;
inline constexpr int hardware_supported_minor = 1;
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
  std::string fault = "none";  // "none", "unresponsive", "vanished", "weak_supply", "stalled_link",
                               // "hung_bus"
  std::uint32_t firmware = 0x0102'0000;  // FW_VERSION, from "1.2.0"
  double fill_words_per_s = 20'000.0;
  double drain_words_per_s = 1'000'000.0;
};

struct HardwareConfig {
  std::string backend = "simulated";  // "simulated" or "mmio"
  std::vector<BoardConfig> boards;
  hw::SlowControlSettings settings;
  std::chrono::milliseconds trigger_timeout{2'000};
  std::chrono::milliseconds drain_timeout{2'000};
};

[[nodiscard]] Expected<HardwareConfig, ConfigErrors> parse_hardware_config(
    std::string_view json_text);

}  // namespace minidaq::config
