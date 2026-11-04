// SPDX-License-Identifier: MIT
// Chapter 33: what the readout link keeps of a single, so that an offline chain can be compared
// with the server record for record.
#include <gtest/gtest.h>

#include <cstdint>
#include <stdexcept>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/readout_link.hpp"

namespace {

using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::Picoseconds;
using minidaq::sim::TruthSingle;

TruthSingle single(std::int64_t t_ps, std::uint32_t crystal, float kev, std::uint64_t decay = 7) {
  TruthSingle s;
  s.single = {Picoseconds{t_ps}, CrystalId{crystal}, KeV{kev}};
  s.decay = decay;
  s.photon = 1;
  s.scattered = true;
  return s;
}

TEST(QuantizeAsOnLink, TruncatesTimeTo5PsAndRoundsEnergyToHalfKeVKeepingTheTruth) {
  // REQ: SRS-SIM-024
  std::vector<TruthSingle> s{single(1'234'567, 100, 511.24F), single(1'234'569, 18'431, 511.26F),
                             single(9'999'999, 5, 435.0F)};
  minidaq::sim::quantize_as_on_link(s);
  EXPECT_EQ(s[0].single.time, Picoseconds{1'234'565});
  EXPECT_EQ(s[1].single.time, Picoseconds{1'234'565});
  EXPECT_EQ(s[2].single.time, Picoseconds{9'999'995});
  EXPECT_FLOAT_EQ(s[0].single.energy.count(), 511.0F);
  EXPECT_FLOAT_EQ(s[1].single.energy.count(), 511.5F);
  EXPECT_FLOAT_EQ(s[2].single.energy.count(), 435.0F);
  EXPECT_EQ(s[1].single.crystal, CrystalId{18'431});
  EXPECT_EQ(s[0].decay, 7U);
  EXPECT_EQ(s[0].photon, 1U);
  EXPECT_TRUE(s[0].scattered);
}

TEST(QuantizeAsOnLink, GivesWhatTheServersDecoderGivesAcrossTheTimeWrap) {
  // REQ: SRS-SIM-024
  // Singles 0.4 s apart over 3 s cross the 38-bit time counter's wrap (1.374 s) twice.
  std::vector<TruthSingle> s;
  std::vector<std::uint64_t> words;
  for (std::int64_t k = 0; k < 8; ++k) {
    s.push_back(single(k * 400'000'000'003, static_cast<std::uint32_t>(k * 1000),
                       300.3F + static_cast<float>(k)));
    words.push_back(minidaq::packed::encode(s.back().single));
  }
  minidaq::packed::StreamDecoder decoder{minidaq::ScannerGeometry::num_crystals};
  std::vector<minidaq::Single> expected(words.size());
  ASSERT_EQ(decoder.decode(words, expected), words.size());
  minidaq::sim::quantize_as_on_link(s);
  for (std::size_t i = 0; i < s.size(); ++i) {
    EXPECT_EQ(s[i].single, expected[i]) << i;
  }
  EXPECT_EQ(s.back().single.time, Picoseconds{2'800'000'000'020});
}

TEST(QuantizeAsOnLink, RefusesACrystalOutsideTheScanner) {
  // REQ: SRS-SIM-024
  std::vector<TruthSingle> s{single(10, minidaq::ScannerGeometry::num_crystals, 511.0F)};
  EXPECT_THROW(minidaq::sim::quantize_as_on_link(s), std::invalid_argument);
}

}  // namespace
