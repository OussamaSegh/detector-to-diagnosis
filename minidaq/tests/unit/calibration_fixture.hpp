// SPDX-License-Identifier: MIT
// A valid calibration table file for tests (Chapter 26): every crystal 5% above nominal gain, a
// little curvature, and offsets of -300 to +300 ps, with the CRC as the procedure would write it.
#pragma once

#include <array>
#include <cstdio>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

#include "minidaq/core/crc32.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/calibration.hpp"

namespace calibration_fixture {

inline std::string hex(std::uint32_t v) {
  std::array<char, 9> b{};
  (void)std::snprintf(b.data(), b.size(), "%08x", v);
  return b.data();
}

inline nlohmann::json good_table() {
  using minidaq::CrystalCalibration;
  using json = nlohmann::json;
  constexpr std::size_t n = minidaq::ScannerGeometry::num_crystals;
  std::vector<CrystalCalibration> k(n);
  json a = json::array();
  json b = json::array();
  json q = json::array();
  json t = json::array();
  for (std::size_t i = 0; i < n; ++i) {
    k[i] = CrystalCalibration{1.5F, 0.525F, -1.0e-5F, static_cast<std::int32_t>(i % 601) - 300};
    a.push_back(k[i].a_kev);
    b.push_back(k[i].b_kev);
    q.push_back(k[i].q_kev);
    t.push_back(k[i].time_offset_ps);
  }
  return json{{"schema_version", "1.0"},
              {"id", "CAL-0001"},
              {"version", 3},
              {"scanner_serial", "MDQ-REF-0001"},
              {"created_utc", "2026-11-03T08:00:00Z"},
              {"valid_until_utc", "2999-12-31T00:00:00Z"},
              {"reference_temperature_c", 25.0},
              {"procedure", "CP-026 version 1"},
              {"crystals", n},
              {"energy", {{"a_kev", a}, {"b_kev", b}, {"q_kev", q}}},
              {"time", {{"offset_ps", t}}},
              {"crc32", hex(minidaq::crc32(minidaq::canonical_bytes(k)))}};
}

}  // namespace calibration_fixture
