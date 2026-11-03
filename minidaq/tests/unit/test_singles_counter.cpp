// SPDX-License-Identifier: MIT
// The singles of each crystal and the run record's corrections object (Chapter 27).
#include <gtest/gtest.h>

#include <limits>
#include <numeric>
#include <vector>

#include "minidaq/control/corrections_record.hpp"
#include "minidaq/processing/singles_counter.hpp"

using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::Picoseconds;
using minidaq::ScannerGeometry;
using minidaq::Single;
using minidaq::SinglesCounter;

namespace {

Single at(std::uint32_t crystal, float kev, std::int64_t ps) {
  return Single{Picoseconds{ps}, CrystalId{crystal}, KeV{kev}};
}

}  // namespace

TEST(SinglesCounter, CountsEachCrystalsSinglesInTheEnergyWindowOnly) {
  // REQ: SRS-COR-001
  SinglesCounter c{435.0, 585.0};
  const float nan = std::numeric_limits<float>::quiet_NaN();
  const std::uint32_t last = ScannerGeometry::num_crystals - 1;
  c.record(std::vector<Single>{at(0, 511.0F, 900), at(0, 435.0F, 1'000), at(0, 585.0F, 1'100),
                               at(0, 434.9F, 1'200), at(0, 585.1F, 1'300), at(7, nan, 1'400),
                               at(last, 500.0F, 1'500), at(ScannerGeometry::num_crystals, 511.0F, 1'600)});
  c.record(std::vector<Single>{at(7, 511.0F, 800), at(7, 511.0F, 2'000)});  // not in time order
  const auto s = c.snapshot();
  ASSERT_EQ(s.per_crystal.size(), ScannerGeometry::num_crystals);
  EXPECT_EQ(s.per_crystal[0], 3U);
  EXPECT_EQ(s.per_crystal[7], 2U);
  EXPECT_EQ(s.per_crystal[last], 1U);
  EXPECT_EQ(s.total, 6U);
  EXPECT_EQ(std::accumulate(s.per_crystal.begin(), s.per_crystal.end(), std::uint64_t{0}), s.total);
  EXPECT_EQ(s.first_ps, 800);
  EXPECT_EQ(s.last_ps, 2'000);
  // Per block, every single of a valid crystal counts, whatever its energy.
  ASSERT_EQ(s.per_block.size(), ScannerGeometry::num_blocks);
  EXPECT_EQ(s.per_block[0], 8U);
  EXPECT_EQ(s.per_block[ScannerGeometry::num_blocks - 1], 1U);
  EXPECT_EQ(std::accumulate(s.per_block.begin(), s.per_block.end(), std::uint64_t{0}), 9U);
}

TEST(SinglesCounter, AnEmptyRunHasNoTimes) {
  // REQ: SRS-COR-001
  const SinglesCounter c{435.0, 585.0};
  const auto s = c.snapshot();
  EXPECT_EQ(s.total, 0U);
  EXPECT_EQ(s.first_ps, 0);
  EXPECT_EQ(s.last_ps, 0);
}

TEST(SinglesCounter, ASingleOutsideTheWindowCountsForItsBlockOnly) {
  // REQ: SRS-COR-001
  SinglesCounter c{435.0, 585.0};
  c.record(std::vector<Single>{at(17, 100.0F, 5)});
  const auto s = c.snapshot();
  EXPECT_EQ(s.total, 0U);
  EXPECT_EQ(s.per_crystal[17], 0U);
  EXPECT_EQ(s.per_block[ScannerGeometry::block_of(CrystalId{17})], 1U);
  EXPECT_EQ(s.first_ps, 5);
  EXPECT_EQ(s.last_ps, 5);
}

TEST(CorrectionsRecord, NamesTheWindowsAndCarriesEveryCrystal) {
  // REQ: SRS-COR-002
  SinglesCounter c{440.0, 600.0};
  c.record(std::vector<Single>{at(3, 511.0F, 10), at(3, 511.0F, 30)});
  minidaq::SorterConfig cfg;
  cfg.energy_low_kev = 440.0;
  cfg.energy_high_kev = 600.0;
  cfg.window = Picoseconds{3'000};
  cfg.delay = Picoseconds{50'000};
  minidaq::SorterStats st;
  st.prompts = 12;
  st.delayed = 4;
  const auto j = minidaq::control::corrections_record(c.snapshot(), cfg, st);
  EXPECT_EQ(j["format"], 1);
  EXPECT_EQ(j["energy_window_kev"], (nlohmann::json{440.0, 600.0}));
  EXPECT_EQ(j["coincidence_window_ps"], 3'000);
  EXPECT_EQ(j["window_mode"], "fixed");
  EXPECT_EQ(j["delayed_window_ps"], 50'000);
  EXPECT_EQ(j["singles_in_window"], 2);
  EXPECT_EQ(j["singles_first_ps"], 10);
  EXPECT_EQ(j["singles_last_ps"], 30);
  ASSERT_EQ(j["singles_per_crystal"].size(), ScannerGeometry::num_crystals);
  EXPECT_EQ(j["singles_per_crystal"][3], 2);
  ASSERT_EQ(j["singles_per_block"].size(), ScannerGeometry::num_blocks);
  EXPECT_EQ(j["singles_per_block"][0], 2);
  EXPECT_EQ(j["prompts"], 12);
  EXPECT_EQ(j["delayeds"], 4);
}
