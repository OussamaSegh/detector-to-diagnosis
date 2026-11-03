// SPDX-License-Identifier: MIT
// MiniDAQ - the calibration table file (Chapter 26).
#include "minidaq/config/calibration_file.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <nlohmann/json.hpp>
#include <vector>

#include "minidaq/core/crc32.hpp"
#include "object_reader.hpp"

namespace minidaq::config {

namespace {

using detail::json;
using detail::ObjectReader;

std::string hex32(std::uint32_t v) {
  std::array<char, 9> buf{};
  (void)std::snprintf(buf.data(), buf.size(), "%08x", v);
  return std::string{buf.data()};
}

// [snippet:arrays]
// One array of exactly `n` numbers into the field `member` of each entry. Each value goes through
// a double first: a float or an int32 gets it only when it fits, so that 1e39 or 3e9 is an error
// and not an infinity or a wrapped integer.
template <typename T>
void read_array(const json& parent, std::string_view key, const std::string& at, std::size_t n,
                std::vector<CrystalCalibration>& out, T CrystalCalibration::*member,
                ConfigErrors& errors) {
  const auto it = parent.find(key);
  const std::string path = at + "/" + std::string{key};
  if (it == parent.end()) {
    errors.push_back({path, "is required"});
    return;
  }
  if (!it->is_array() || it->size() != n) {
    errors.push_back({path, "must be an array of " + std::to_string(n) + " numbers"});
    return;
  }
  std::size_t bad = 0;
  for (std::size_t i = 0; i < n; ++i) {
    const json& v = (*it)[i];
    bool ok = false;
    if constexpr (std::is_floating_point_v<T>) {
      if (v.is_number()) {
        const double d = v.get<double>();
        ok = std::isfinite(d) && std::abs(d) <= static_cast<double>(std::numeric_limits<T>::max());
        if (ok) {
          out[i].*member = static_cast<T>(d);
        }
      }
    } else {
      if (v.is_number_integer()) {
        const auto x = v.get<std::int64_t>();
        ok = x >= std::numeric_limits<T>::min() && x <= std::numeric_limits<T>::max();
        if (ok) {
          out[i].*member = static_cast<T>(x);
        }
      }
    }
    if (!ok && ++bad <= 5) {
      errors.push_back({path + "/" + std::to_string(i), std::is_floating_point_v<T>
                                                            ? "must be a finite number"
                                                            : "must be an integer of 32 bits"});
    }
  }
  if (bad > 5) {
    errors.push_back({path, "and " + std::to_string(bad - 5) + " more values"});
  }
}
// [/snippet:arrays]

}  // namespace

// [snippet:parse]
Expected<CalibrationTable, ConfigErrors> parse_calibration(std::string_view json_text) {
  json doc;
  try {
    doc = json::parse(json_text);
  } catch (const json::exception& e) {
    return Unexpected{ConfigErrors{{"", std::string{"not valid JSON: "} + e.what()}}};
  }
  ConfigErrors errors;
  ObjectReader top{doc, "", errors};
  std::string version;
  top.get("schema_version", version);
  int major = 0;
  int minor = 0;
  if (doc.is_object() && !doc.contains("schema_version")) {
    errors.push_back({"/schema_version", "is required"});
  } else if (doc.is_object() && doc["schema_version"].is_string() &&
             (!detail::parse_version(version, major, minor) ||
              major != calibration_supported_major || minor > calibration_supported_minor)) {
    errors.push_back({"/schema_version", "must be \"1.0\""});
  }
  CalibrationInfo info;
  top.get("id", info.id);
  top.get("version", info.version, std::uint32_t{1}, std::numeric_limits<std::uint32_t>::max());
  top.get("scanner_serial", info.scanner_serial);
  top.get("created_utc", info.created_utc);
  top.get("valid_until_utc", info.valid_until_utc);
  top.get("reference_temperature_c", info.reference_temperature_c, -40.0, 125.0);
  top.get("procedure", info.procedure);
  for (const char* key : {"id", "version", "scanner_serial", "created_utc", "valid_until_utc",
                          "reference_temperature_c", "procedure"}) {
    if (doc.is_object() && !doc.contains(key)) {
      errors.push_back({std::string{"/"} + key, "is required"});
    }
  }
  std::uint64_t crystals = 0;
  top.get("crystals", crystals, std::uint64_t{1}, std::uint64_t{1} << 20U);
  if (doc.is_object() && crystals != ScannerGeometry::num_crystals) {
    errors.push_back({"/crystals", "must be " + std::to_string(ScannerGeometry::num_crystals) +
                                       ", the crystals of this scanner"});
  }
  std::string crc_text;
  top.get("crc32", crc_text);
  std::vector<CrystalCalibration> k(ScannerGeometry::num_crystals);
  const std::size_t n = k.size();
  if (const json* e = top.object("energy")) {
    ObjectReader r{*e, "/energy", errors};
    (void)r.object("a_kev");  // read below, as arrays; named here so that finish() knows them
    (void)r.object("b_kev");
    (void)r.object("q_kev");
    r.finish();
    if (e->is_object()) {
      read_array(*e, "a_kev", "/energy", n, k, &CrystalCalibration::a_kev, errors);
      read_array(*e, "b_kev", "/energy", n, k, &CrystalCalibration::b_kev, errors);
      read_array(*e, "q_kev", "/energy", n, k, &CrystalCalibration::q_kev, errors);
    }
  } else if (doc.is_object()) {
    errors.push_back({"/energy", "is required"});
  }
  if (const json* t = top.object("time")) {
    ObjectReader r{*t, "/time", errors};
    (void)r.object("offset_ps");
    r.finish();
    if (t->is_object()) {
      read_array(*t, "offset_ps", "/time", n, k, &CrystalCalibration::time_offset_ps, errors);
    }
  } else if (doc.is_object()) {
    errors.push_back({"/time", "is required"});
  }
  top.finish();
  if (!errors.empty()) {
    return Unexpected{std::move(errors)};
  }
  // The CRC last: over the values as this program read them, so that it also catches a number
  // that the writer and this reader would round differently.
  if (const std::string got = hex32(minidaq::crc32(canonical_bytes(k))); got != crc_text) {
    return Unexpected{
        ConfigErrors{{"/crc32", "is \"" + crc_text + "\", the coefficients give \"" + got +
                                    "\": the table is damaged or was edited by hand"}}};
  }
  auto table = CalibrationTable::make(std::move(info), std::move(k));
  if (!table) {
    for (auto& m : table.error()) {
      errors.push_back({"", std::move(m)});
    }
    return Unexpected{std::move(errors)};
  }
  return std::move(*table);
}
// [/snippet:parse]

nlohmann::json to_json(const CalibrationTable& t) {
  const CalibrationInfo& i = t.info();
  return json{{"id", i.id},
              {"version", i.version},
              {"scanner_serial", i.scanner_serial},
              {"created_utc", i.created_utc},
              {"valid_until_utc", i.valid_until_utc},
              {"reference_temperature_c", i.reference_temperature_c},
              {"procedure", i.procedure},
              {"crc32", hex32(t.crc32())},
              {"time_spread_ps", t.time_spread_ps()}};
}

}  // namespace minidaq::config
