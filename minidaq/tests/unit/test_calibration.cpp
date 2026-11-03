// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <string>
#include <vector>

#include "minidaq/core/crc32.hpp"
#include "minidaq/processing/calibration.hpp"

using minidaq::CalibrationInfo;
using minidaq::CalibrationLimits;
using minidaq::CalibrationTable;
using minidaq::CrystalCalibration;
using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::PhotopeakMonitor;
using minidaq::Picoseconds;
using minidaq::ScannerGeometry;
using minidaq::Single;

namespace {

CalibrationInfo good_info() {
  return CalibrationInfo{
      "CAL-0001",        3, "MDQ-REF-0001", "2026-11-03T08:00:00Z", "2026-12-03T08:00:00Z", 25.0,
      "CP-026 version 1"};
}

std::vector<CrystalCalibration> nominal() {
  return std::vector<CrystalCalibration>(ScannerGeometry::num_crystals);
}

bool mentions(const std::vector<std::string>& errors, const std::string& text) {
  for (const auto& e : errors) {
    if (e.find(text) != std::string::npos) {
      return true;
    }
  }
  return false;
}

Single at(std::uint32_t crystal, float energy_kev, std::int64_t time_ps) {
  return Single{Picoseconds{time_ps}, CrystalId{crystal}, KeV{energy_kev}};
}

}  // namespace

TEST(Calibration, TheIdentityTableChangesNothing) {
  // REQ: SRS-CAL-002
  const CalibrationTable t = CalibrationTable::identity();
  EXPECT_TRUE(t.is_identity());
  EXPECT_EQ(t.time_spread_ps(), 0);
  for (const float e : {0.0F, 0.5F, 255.5F, 511.0F, 1023.5F}) {
    Single s = at(17, e, 123'456);
    t.apply(s);
    EXPECT_EQ(s, at(17, e, 123'456)) << e;
  }
}

TEST(Calibration, AppliesEachCrystalsOwnEnergyCurveAndTimeOffset) {
  // REQ: SRS-CAL-002
  // REQ: SRS-CAL-003
  auto k = nominal();
  k[5] = CrystalCalibration{2.0F, 0.6F, -2.0e-5F, 350};
  k[6] = CrystalCalibration{-1.0F, 0.45F, 0.0F, -420};
  const auto t = CalibrationTable::make(good_info(), k);
  ASSERT_TRUE(t) << t.error().front();

  Single s = at(5, 400.0F, 1'000'000);  // code 800
  t->apply(s);
  EXPECT_FLOAT_EQ(s.energy.count(), 2.0F + 800.0F * (0.6F + 800.0F * -2.0e-5F));
  EXPECT_EQ(s.time.count(), 1'000'000 - 350);

  Single u = at(6, 400.0F, 1'000'000);
  t->apply(u);
  EXPECT_FLOAT_EQ(u.energy.count(), -1.0F + 800.0F * 0.45F);
  EXPECT_EQ(u.time.count(), 1'000'000 + 420);

  Single other = at(7, 400.0F, 1'000'000);  // nominal entry
  t->apply(other);
  EXPECT_EQ(other, at(7, 400.0F, 1'000'000));
  EXPECT_EQ(t->time_spread_ps(), 350 + 420);
}

TEST(Calibration, ASingleOfACrystalOutsideTheScannerIsLeftAlone) {
  auto k = nominal();
  for (auto& e : k) {
    e.time_offset_ps = 100;
  }
  const auto t = CalibrationTable::make(good_info(), k);
  ASSERT_TRUE(t);
  Single s = at(ScannerGeometry::num_crystals, 300.0F, 5'000);
  t->apply(s);
  EXPECT_EQ(s, at(ScannerGeometry::num_crystals, 300.0F, 5'000));
}

TEST(Calibration, RefusesATableForAnotherNumberOfCrystals) {
  // REQ: SRS-CAL-001
  const auto t = CalibrationTable::make(good_info(), std::vector<CrystalCalibration>(100));
  ASSERT_FALSE(t);
  EXPECT_TRUE(mentions(t.error(), "has 100 crystals"));
}

TEST(Calibration, RefusesEachCoefficientOutsideWhatADetectorCanHave) {
  // REQ: SRS-CAL-001
  const float nan = std::numeric_limits<float>::quiet_NaN();
  const struct {
    CrystalCalibration entry;
    const char* message;
  } cases[] = {
      {{0.0F, 0.24F, 0.0F, 0}, "gain"},  // gain 0.48
      {{0.0F, 1.01F, 0.0F, 0}, "gain"},  // gain 2.02
      {{nan, 0.5F, 0.0F, 0}, "finite"},
      {{0.0F, std::numeric_limits<float>::infinity(), 0.0F, 0}, "finite"},
      {{0.0F, 0.5F, nan, 0}, "finite"},
      {{101.0F, 0.5F, 0.0F, 0}, "code 0"},
      {{-101.0F, 0.5F, 0.0F, 0}, "code 0"},
      {{0.0F, 0.5F, -1.3e-4F, 0}, "falls"},         // slope < 0 before 2047
      {{0.0F, 0.5F, -1.0e-4F, 0}, "nonlinearity"},  // 41% below linear at the top
      {{0.0F, 0.5F, 3.7e-4F, 0}, "nonlinearity"},   // 151% above
      {{0.0F, 0.5F, 0.0F, 5'001}, "time offset"},
      {{0.0F, 0.5F, 0.0F, -5'001}, "time offset"},
  };
  for (const auto& c : cases) {
    auto k = nominal();
    k[42] = c.entry;
    const auto t = CalibrationTable::make(good_info(), k);
    ASSERT_FALSE(t) << c.message;
    EXPECT_TRUE(mentions(t.error(), "crystal 42: ")) << c.message;
    EXPECT_TRUE(mentions(t.error(), c.message)) << t.error().front();
  }
  // The limits themselves are accepted.
  auto k = nominal();
  k[1] = {100.0F, 0.25F, 0.0F, 5'000};
  k[2] = {-100.0F, 1.0F, -0.39F * 1.0F / 2047.0F, -5'000};
  k[3] = {0.0F, 0.5F, 1.49F * 0.5F / 2047.0F, 0};
  // The curve tools/calib fits to a crystal of gain 0.6 behind a SiPM with E_sat 1500 keV: its
  // quadratic term is 1.15 times its linear term at the top code.
  k[4] = {13.06F, 0.742F, 1.15F * 0.742F / 2047.0F, 0};
  EXPECT_TRUE(CalibrationTable::make(good_info(), k));
}

TEST(Calibration, ReportsTwentyRefusedCrystalsAndCountsTheRest) {
  auto k = nominal();
  for (std::size_t i = 0; i < 25; ++i) {
    k[i].b_kev = 0.0F;
  }
  const auto t = CalibrationTable::make(good_info(), k);
  ASSERT_FALSE(t);
  EXPECT_EQ(t.error().size(), 21U);
  EXPECT_TRUE(mentions(t.error(), "and 5 more crystals"));
}

TEST(Calibration, RefusesATableThatDoesNotSayWhereAndWhenItWasMade) {
  // REQ: SRS-CAL-001
  struct Case {
    void (*edit)(CalibrationInfo&);
    const char* message;
  };
  const Case cases[] = {
      {[](CalibrationInfo& i) { i.id.clear(); }, "must not be empty"},
      {[](CalibrationInfo& i) { i.scanner_serial.clear(); }, "must not be empty"},
      {[](CalibrationInfo& i) { i.procedure.clear(); }, "must not be empty"},
      {[](CalibrationInfo& i) { i.created_utc = "2026-11-03 08:00:00"; }, "created_utc"},
      {[](CalibrationInfo& i) { i.valid_until_utc = "soon"; }, "valid_until_utc"},
      {[](CalibrationInfo& i) { i.valid_until_utc = i.created_utc; }, "not after"},
      {[](CalibrationInfo& i) { i.reference_temperature_c = 130.0; }, "reference_temperature"},
      {[](CalibrationInfo& i) { i.reference_temperature_c = std::nan(""); },
       "reference_temperature"},
  };
  for (const Case& c : cases) {
    CalibrationInfo info = good_info();
    c.edit(info);
    const auto t = CalibrationTable::make(info, nominal());
    ASSERT_FALSE(t) << c.message;
    EXPECT_TRUE(mentions(t.error(), c.message)) << t.error().front();
  }
}

TEST(Calibration, ItsCrcIsThatOfTheCanonicalBytesAsPythonWritesThem) {
  // REQ: SRS-CAL-001
  // Reference values from Python: zlib.crc32(b"".join(struct.pack("<fffi", ...))).
  EXPECT_EQ(CalibrationTable::identity().crc32(), 0x6c696a72U);
  auto k = nominal();
  for (std::size_t i = 0; i < k.size(); ++i) {
    k[i] = CrystalCalibration{1.5F, 0.55F, -1e-5F, static_cast<std::int32_t>(i % 7) - 3};
  }
  const auto t = CalibrationTable::make(good_info(), k);
  ASSERT_TRUE(t);
  EXPECT_EQ(t->crc32(), 0x0358327dU);
  EXPECT_EQ(minidaq::canonical_bytes(t->crystals()).size(), 16U * ScannerGeometry::num_crystals);
}

TEST(Calibration, KnowsAUtcTimestampWhenItSeesOne) {
  using minidaq::is_utc_timestamp;
  EXPECT_TRUE(is_utc_timestamp("2026-11-03T08:00:00Z"));
  EXPECT_TRUE(is_utc_timestamp("2028-02-29T23:59:59Z"));
  EXPECT_TRUE(is_utc_timestamp("2000-02-29T00:00:00Z"));
  for (const char* bad : {"2027-02-29T00:00:00Z", "1900-02-29T00:00:00Z", "2026-13-01T00:00:00Z",
                          "2026-00-01T00:00:00Z", "2026-04-31T00:00:00Z", "2026-11-00T00:00:00Z",
                          "2026-11-03T24:00:00Z", "2026-11-03T08:60:00Z", "2026-11-03T08:00:60Z",
                          "2026-11-03T08:00:00", "2026-11-03T08:00:00+01:00",
                          "2026-11-03 08:00:00Z", "2026/11/03T08:00:00Z", "2026-11-03T08-00:00Z",
                          "2026-11-03T08:00-00Z", "2026-1x-03T08:00:00Z", "", "20261103T080000Z"}) {
    EXPECT_FALSE(is_utc_timestamp(bad)) << bad;
  }
}

TEST(PhotopeakMonitor, AveragesThePhotopeakOfEachBlockOnly) {
  // REQ: SRS-CAL-006
  PhotopeakMonitor m;
  const std::uint32_t block0 = 0;  // ring 0, transaxial 0
  const std::uint32_t block1 = ScannerGeometry::make_crystal(0, 16).value();
  const std::uint32_t block24 = ScannerGeometry::make_crystal(16, 0).value();
  std::vector<Single> v{
      at(block0, 500.0F, 0), at(block0, 520.0F, 1),  at(block0, 300.0F, 2),
      at(block0, 429.9F, 3), at(block0, 590.1F, 4),  at(block1, 430.0F, 5),
      at(block1, 590.0F, 6), at(block24, 480.0F, 7), at(ScannerGeometry::num_crystals, 511.0F, 8)};
  m.record(v);
  m.record(std::vector<Single>{at(block0, 510.0F, 9)});
  const auto s = m.snapshot();
  EXPECT_EQ(s[0].singles, 3U);
  EXPECT_DOUBLE_EQ(s[0].mean_kev, (500.0 + 520.0 + 510.0) / 3.0);
  EXPECT_EQ(s[1].singles, 2U);
  EXPECT_DOUBLE_EQ(s[1].mean_kev, 510.0);
  EXPECT_EQ(s[24].singles, 1U);
  EXPECT_EQ(s[2].singles, 0U);
  EXPECT_EQ(s[2].mean_kev, 0.0);
  m.reset();
  EXPECT_EQ(m.snapshot()[0].singles, 0U);
}
