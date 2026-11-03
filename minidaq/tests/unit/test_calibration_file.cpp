// SPDX-License-Identifier: MIT
// The calibration table file and what the acquisition service does with it (Chapter 26).
#include <gtest/gtest.h>
#include <unistd.h>

#include <array>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>
#include <string>

#include "calibration_fixture.hpp"
#include "eventually.hpp"
#include "minidaq/config/calibration_file.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/core/crc32.hpp"

using namespace minidaq;
using json = nlohmann::json;

namespace {

constexpr std::size_t n = ScannerGeometry::num_crystals;
using calibration_fixture::good_table;
using calibration_fixture::hex;

// Recomputes the CRC after an edit of the coefficients, as a careful forger would.
void reseal(json& j) {
  std::vector<CrystalCalibration> k(n);
  for (std::size_t i = 0; i < n; ++i) {
    k[i] = CrystalCalibration{
        j["energy"]["a_kev"][i].get<float>(), j["energy"]["b_kev"][i].get<float>(),
        j["energy"]["q_kev"][i].get<float>(), j["time"]["offset_ps"][i].get<std::int32_t>()};
  }
  j["crc32"] = hex(crc32(canonical_bytes(k)));
}

bool has(const config::ConfigErrors& e, const std::string& path, const std::string& text) {
  for (const auto& x : e) {
    if (x.path == path && x.message.find(text) != std::string::npos) {
      return true;
    }
  }
  return false;
}

config::ConfigErrors errors_of(const json& j) {
  auto t = config::parse_calibration(j.dump());
  return t ? config::ConfigErrors{} : t.error();
}

// A file of its own per test and process, removed at the end.
struct TempFile {
  std::filesystem::path path;
  explicit TempFile(const std::string& name, const std::string& text)
      : path{std::filesystem::temp_directory_path() /
             (name + "-" + std::to_string(::getpid()) + ".json")} {
    std::ofstream{path} << text;
  }
  ~TempFile() { std::filesystem::remove(path); }
  TempFile(const TempFile&) = delete;
  TempFile& operator=(const TempFile&) = delete;
  TempFile(TempFile&&) = delete;
  TempFile& operator=(TempFile&&) = delete;
};

config::AcquisitionConfig with_table(const TempFile& f, std::string serial = "MDQ-REF-0001") {
  config::AcquisitionConfig c;
  c.source.rate_hz = 2e6;
  c.stop_after_s = 0.2;
  c.calibration.file = f.path.string();
  c.calibration.scanner_serial = std::move(serial);
  return c;
}

}  // namespace

TEST(CalibrationFile, ReadsATableAsTheProcedureWritesIt) {
  // REQ: SRS-CAL-001
  const auto t = config::parse_calibration(good_table().dump());
  ASSERT_TRUE(t) << config::format_errors(t.error());
  EXPECT_EQ(t->info().id, "CAL-0001");
  EXPECT_EQ(t->info().version, 3U);
  EXPECT_EQ(t->info().scanner_serial, "MDQ-REF-0001");
  EXPECT_EQ(t->crystals()[7], (CrystalCalibration{1.5F, 0.525F, -1.0e-5F, 7 - 300}));
  EXPECT_EQ(t->time_spread_ps(), 600);
  const json id = config::to_json(*t);
  EXPECT_EQ(id["crc32"], good_table()["crc32"]);
  EXPECT_EQ(id["procedure"], "CP-026 version 1");
}

TEST(CalibrationFile, RefusesADamagedOrHandEditedTable) {
  // REQ: SRS-CAL-001
  json j = good_table();
  j["energy"]["b_kev"][100] = 0.53;  // one value changed, the CRC not
  EXPECT_TRUE(has(errors_of(j), "/crc32", "damaged or was edited by hand"));
  j = good_table();
  j["crc32"] = "00000000";
  EXPECT_TRUE(has(errors_of(j), "/crc32", "the coefficients give"));
  // A value that a reader would round differently from the writer's float is caught too.
  j = good_table();
  j["energy"]["b_kev"][5] = 0.5250000001;
  EXPECT_TRUE(errors_of(j).empty()) << "rounds to the same float: the same table";
  j["energy"]["b_kev"][5] = 0.52501;
  EXPECT_TRUE(has(errors_of(j), "/crc32", "damaged"));
}

TEST(CalibrationFile, RefusesEachMalformedPart) {
  // REQ: SRS-CAL-001
  const struct {
    void (*edit)(json&);
    const char* path;
    const char* message;
  } cases[] = {
      {[](json& j) { j["schema_version"] = "2.0"; }, "/schema_version", "must be \"1.0\""},
      {[](json& j) { j["schema_version"] = "1.1"; }, "/schema_version", "must be \"1.0\""},
      {[](json& j) { j["schema_version"] = ""; }, "/schema_version", "must be \"1.0\""},
      {[](json& j) { j.erase("schema_version"); }, "/schema_version", "is required"},
      {[](json& j) { j["colour"] = 1; }, "/colour", "unknown key"},
      {[](json& j) { j["energy"]["c_kev"] = json::array(); }, "/energy/c_kev", "unknown key"},
      {[](json& j) { j["time"]["offst_ps"] = 1; }, "/time/offst_ps", "unknown key"},
      {[](json& j) { j.erase("id"); }, "/id", "is required"},
      {[](json& j) { j.erase("valid_until_utc"); }, "/valid_until_utc", "is required"},
      {[](json& j) { j["version"] = 0; }, "/version", "between"},
      {[](json& j) { j["version"] = -1; }, "/version", "non-negative"},
      {[](json& j) { j["crystals"] = 100; }, "/crystals", "must be 18432"},
      {[](json& j) { j["energy"]["a_kev"].erase(0); }, "/energy/a_kev", "array of 18432"},
      {[](json& j) { j["energy"]["q_kev"] = 0; }, "/energy/q_kev", "array of 18432"},
      {[](json& j) { j["energy"].erase("b_kev"); }, "/energy/b_kev", "is required"},
      {[](json& j) { j.erase("energy"); }, "/energy", "is required"},
      {[](json& j) { j.erase("time"); }, "/time", "is required"},
      {[](json& j) { j["energy"] = 1; }, "/energy", "must be an object"},
      {[](json& j) { j["energy"]["a_kev"][3] = "1"; }, "/energy/a_kev/3", "finite number"},
      {[](json& j) { j["energy"]["a_kev"][3] = 1e39; }, "/energy/a_kev/3", "finite number"},
      {[](json& j) { j["time"]["offset_ps"][9] = 1.5; }, "/time/offset_ps/9", "integer of 32 bits"},
      {[](json& j) { j["time"]["offset_ps"][9] = 3'000'000'000LL; }, "/time/offset_ps/9",
       "32 bits"},
      {[](json& j) { j["time"]["offset_ps"][9] = -3'000'000'000LL; }, "/time/offset_ps/9",
       "32 bits"},
      {[](json& j) { j["schema_version"] = 1; }, "/schema_version", "must be a string"},
      {[](json& j) { j["time"] = 1; }, "/time", "must be an object"},
      {[](json& j) { j["reference_temperature_c"] = 200; }, "/reference_temperature_c", "between"},
  };
  for (const auto& c : cases) {
    json j = good_table();
    c.edit(j);
    EXPECT_TRUE(has(errors_of(j), c.path, c.message))
        << c.path << ": " << config::format_errors(errors_of(j));
  }
  EXPECT_FALSE(config::parse_calibration("{not json"));
  EXPECT_TRUE(has(errors_of(json::array()), "", "must be an object"));
}

TEST(CalibrationFile, ReportsAtMostFiveBadValuesPerArray) {
  json j = good_table();
  for (std::size_t i = 0; i < 8; ++i) {
    j["energy"]["a_kev"][i] = nullptr;
  }
  const auto e = errors_of(j);
  EXPECT_TRUE(has(e, "/energy/a_kev/4", "finite"));
  EXPECT_FALSE(has(e, "/energy/a_kev/5", "finite"));
  EXPECT_TRUE(has(e, "/energy/a_kev", "and 3 more values"));
}

TEST(CalibrationFile, ACorrectlySealedTableIsStillCheckedAgainstTheLimits) {
  // REQ: SRS-CAL-001
  json j = good_table();
  j["energy"]["b_kev"][42] = 2.0;  // gain 4
  j["created_utc"] = "yesterday";
  reseal(j);
  const auto e = errors_of(j);
  EXPECT_TRUE(has(e, "", "crystal 42: gain")) << config::format_errors(e);
  EXPECT_TRUE(has(e, "", "created_utc"));
}

TEST(CalibrationService, ConfiguresWithATableAndReportsIt) {
  // REQ: SRS-CAL-004
  // REQ: SRS-CAL-006
  const TempFile f{"minidaq-cal-good", good_table().dump()};
  control::AcquisitionService svc{control::with_default_adapters()};
  const auto r = svc.configure(with_table(f), "test");
  ASSERT_TRUE(r.ok) << r.message;
  auto st = svc.status();
  EXPECT_EQ(st["calibration"]["id"], "CAL-0001");
  EXPECT_EQ(st["calibration"]["version"], 3);
  EXPECT_EQ(st["calibration"]["crc32"], good_table()["crc32"]);
  EXPECT_FALSE(st["calibration"].contains("photopeak")) << "no run yet";
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(control::AcqState::configured, test_support::patience))
      << svc.status().dump();
  st = svc.status();
  const auto& p = st["calibration"]["photopeak"];
  ASSERT_EQ(p["blocks"].size(), ScannerGeometry::num_blocks);
  std::uint64_t in_window = 0;
  for (const auto& b : p["blocks"]) {
    in_window += b["singles"].get<std::uint64_t>();
  }
  EXPECT_GT(in_window, 10'000U);
  // The synthetic source reports calibrated energies; a 5% gain error moves each block's
  // photopeak by about that much: every block with enough singles is named.
  EXPECT_FALSE(p["drifted_blocks"].empty()) << p.dump();
  EXPECT_EQ(st["calibration"]["drift_tolerance_percent"], 2.0);
}

TEST(CalibrationService, NamesNoBlockWhenTheTableIsRight) {
  // REQ: SRS-CAL-006
  control::AcquisitionService svc{control::with_default_adapters()};
  config::AcquisitionConfig c;
  c.source.rate_hz = 2e6;
  c.stop_after_s = 0.2;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  EXPECT_EQ(svc.status()["calibration"]["id"], "identity");
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(control::AcqState::configured, test_support::patience));
  const auto st = svc.status();
  EXPECT_TRUE(st["calibration"]["photopeak"]["drifted_blocks"].empty()) << st["calibration"].dump();
}

TEST(CalibrationService, RefusesATableForAnotherScannerOrOutOfDate) {
  // REQ: SRS-CAL-004
  const TempFile f{"minidaq-cal-serial", good_table().dump()};
  control::AcquisitionService svc{control::with_default_adapters()};
  auto r = svc.configure(with_table(f, "MDQ-REF-0002"), "test");
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, "config_error");
  EXPECT_NE(r.message.find("made for scanner \"MDQ-REF-0001\""), std::string::npos) << r.message;

  json old = good_table();
  old["valid_until_utc"] = "2026-01-01T00:00:00Z";
  old["created_utc"] = "2025-12-01T00:00:00Z";
  const TempFile g{"minidaq-cal-old", old.dump()};
  r = svc.configure(with_table(g), "test");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.message.find("was valid until 2026-01-01T00:00:00Z"), std::string::npos) << r.message;
  EXPECT_EQ(svc.state(), control::AcqState::idle) << "nothing was configured";
}

TEST(CalibrationService, RefusesAMissingOrDamagedFile) {
  // REQ: SRS-CAL-001
  control::AcquisitionService svc{control::with_default_adapters()};
  config::AcquisitionConfig c;
  c.calibration.file = "/nonexistent/table.json";
  c.calibration.scanner_serial = "MDQ-REF-0001";
  auto r = svc.configure(c, "test");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.message.find("/calibration/file: cannot read"), std::string::npos) << r.message;

  json j = good_table();
  j["time"]["offset_ps"][0] = 1;
  const TempFile f{"minidaq-cal-damaged", j.dump()};
  r = svc.configure(with_table(f), "test");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.message.find("/crc32"), std::string::npos) << r.message;
}

TEST(CalibrationConfig, NeedsTheScannerSerialWithATable) {
  // REQ: SRS-CAL-004
  auto c = config::parse_config(R"({"schema_version": "1.4", "calibration": {"file": "t.json"}})");
  ASSERT_FALSE(c);
  EXPECT_TRUE(has(c.error(), "/calibration/scanner_serial", "is required"));
  c = config::parse_config(
      R"({"schema_version": "1.4", "calibration": {"drift_tolerance_percent": 0}})");
  ASSERT_FALSE(c);
  EXPECT_TRUE(has(c.error(), "/calibration/drift_tolerance_percent", "between"));
  c = config::parse_config(
      R"({"schema_version": "1.4", "calibration": {"file": "t.json", "scanner_serial": "S1", "drift_tolerance_percent": 3}})");
  ASSERT_TRUE(c);
  EXPECT_EQ(c->calibration.file, "t.json");
  EXPECT_EQ(config::to_json(*c)["calibration"]["drift_tolerance_percent"], 3.0);
}
