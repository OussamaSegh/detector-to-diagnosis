// SPDX-License-Identifier: MIT
// MiniDAQ - the calibration table file (Chapter 26; format: docs/formats/calibration.md).
//
// A JSON document that the calibration procedure writes (tools/calib) and the acquisition service
// reads when a configuration names it. It is read as strictly as a configuration: every key known,
// every value of the right type, one value per crystal in each array, and the CRC-32 of the
// coefficients as the procedure wrote them, so that a damaged or hand-edited table is refused.
// The values themselves are checked by CalibrationTable::make().
//
//   {"schema_version": "1.0", "id": "CAL-0001", "version": 3, "scanner_serial": "MDQ-REF-0001",
//    "created_utc": "2026-11-03T08:00:00Z", "valid_until_utc": "2026-12-03T08:00:00Z",
//    "reference_temperature_c": 25.0, "procedure": "CP-026 version 1", "crystals": 18432,
//    "energy": {"a_kev": [...], "b_kev": [...], "q_kev": [...]},
//    "time": {"offset_ps": [...]}, "crc32": "6c696a72"}
#pragma once

#include <cstddef>
#include <string>
#include <string_view>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/processing/calibration.hpp"

namespace minidaq::config {

inline constexpr int calibration_supported_major = 1;
inline constexpr int calibration_supported_minor = 0;
// About 1 MB for 18,432 crystals with the procedure's number format; 8 MiB leaves room.
inline constexpr std::size_t max_calibration_file_bytes = std::size_t{8} << 20U;

[[nodiscard]] Expected<CalibrationTable, ConfigErrors> parse_calibration(
    std::string_view json_text);

// The identity of a table as the run record and the list-mode metadata give it.
[[nodiscard]] nlohmann::json to_json(const CalibrationTable& t);

}  // namespace minidaq::config
