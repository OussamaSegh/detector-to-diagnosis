// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

using namespace minidaq;
using namespace minidaq::literals;
namespace p = minidaq::packed;

static_assert(p::coarse_tick_ps == 5120);
static_assert(p::wrap_period_ps == 1'374'389'534'720);  // 2^38 * 5 ps, about 1.374 s
static_assert(p::energy_max_kev == 1023.5F);
static_assert(ScannerGeometry::num_crystals <= (1U << p::crystal_bits));
static_assert(p::unpack(p::pack({32767, 2047, p::time_mask})).crystal == 32767);

TEST(PackedSingle, FieldsDoNotOverlap) {
  // REQ: SRS-FMT-010
  EXPECT_EQ(p::pack({0x7FFF, 0, 0}) & p::pack({0, 0x7FF, 0}), 0U);
  EXPECT_EQ(p::pack({0, 0x7FF, 0}) & p::pack({0, 0, p::time_mask}), 0U);
  EXPECT_EQ(p::pack({0x7FFF, 0x7FF, p::time_mask}), std::numeric_limits<std::uint64_t>::max());
}

TEST(PackedSingle, CoarseAndFine) {
  const std::uint64_t code = (std::uint64_t{123456} << p::fine_bits) | 789U;
  EXPECT_EQ(p::coarse_of(code), 123456U);
  EXPECT_EQ(p::fine_of(code), 789U);
}

TEST(PackedSingle, RoundTripPropertyWithinQuantization) {
  // REQ: SRS-FMT-011
  std::mt19937_64 rng{42};
  std::uniform_int_distribution<std::int64_t> t_dist(0, p::wrap_period_ps - 1);
  std::uniform_int_distribution<std::uint32_t> c_dist(0, ScannerGeometry::num_crystals - 1);
  std::uniform_real_distribution<float> e_dist(0.0F, 1023.5F);
  for (int i = 0; i < 100'000; ++i) {
    const Single s{Picoseconds{t_dist(rng)}, CrystalId{c_dist(rng)}, KeV{e_dist(rng)}};
    const p::Fields f = p::unpack(p::encode(s));
    EXPECT_EQ(f.crystal, s.crystal.value());
    const auto t = static_cast<std::int64_t>(f.time_code) * p::time_lsb_ps;
    ASSERT_LE(t, s.time.count());
    ASSERT_LT(s.time.count() - t, p::time_lsb_ps);  // truncation error < 1 LSB
    ASSERT_LE(std::fabs(p::energy_of(f.energy_code).count() - s.energy.count()), 0.25F);
  }
}

TEST(PackedSingle, EnergySaturatesAndHandlesNaN) {
  auto e = [](float kev) { return p::unpack(p::encode(Single{0_ps, CrystalId{0}, KeV{kev}})).energy_code; };
  EXPECT_EQ(e(5000.0F), 2047U);
  EXPECT_EQ(e(1023.5F), 2047U);
  EXPECT_EQ(e(-3.0F), 0U);
  EXPECT_EQ(e(std::numeric_limits<float>::quiet_NaN()), 0U);
  EXPECT_EQ(e(511.0F), 1022U);
}

TEST(TimeUnwrapper, ReconstructsAcrossManyWraps) {
  // REQ: SRS-FMT-012
  p::TimeUnwrapper u;
  const std::int64_t step = p::wrap_period_ps / 7;  // < half a period per step
  for (std::int64_t t = 0; t < 20 * p::wrap_period_ps; t += step) {
    const auto code = static_cast<std::uint64_t>(t / p::time_lsb_ps) & p::time_mask;
    ASSERT_EQ(u.unwrap(code).count(), t - t % p::time_lsb_ps) << t;
  }
  EXPECT_EQ(u.epoch(), 19);
}

TEST(TimeUnwrapper, LateWordFromBeforeTheWrap) {
  p::TimeUnwrapper u;
  const std::uint64_t near_end = p::time_mask - 10;
  EXPECT_EQ(u.unwrap(near_end).count(), static_cast<std::int64_t>(near_end) * 5);
  EXPECT_EQ(u.unwrap(5).count(), p::wrap_period_ps + 25);  // wrapped
  // A word stamped just before the wrap arrives late: still epoch 0.
  EXPECT_EQ(u.unwrap(near_end + 3).count(), static_cast<std::int64_t>(near_end + 3) * 5);
  EXPECT_EQ(u.unwrap(6).count(), p::wrap_period_ps + 30);
}

TEST(StreamDecoder, DecodesAndCountsInvalidCrystals) {
  // REQ: SRS-FMT-013
  std::vector<std::uint64_t> words = {
      p::encode(Single{1_ns, CrystalId{10}, 511.0_keV}),
      p::pack({ScannerGeometry::num_crystals, 100, 400}),  // invalid id for this scanner
      p::encode(Single{3_ns, CrystalId{20}, 300.0_keV}),
  };
  std::array<Single, 8> out{};
  p::StreamDecoder d{ScannerGeometry::num_crystals};
  ASSERT_EQ(d.decode(words, out), 2U);
  EXPECT_EQ(out[0].crystal, CrystalId{10});
  EXPECT_EQ(out[0].time, 1_ns);
  EXPECT_EQ(out[1].energy, 300.0_keV);
  EXPECT_EQ(d.stats().words, 3U);
  EXPECT_EQ(d.stats().invalid_crystal, 1U);
}

TEST(StreamDecoder, OutputSpanLimitsTheWork) {
  std::vector<std::uint64_t> words(10, p::encode(Single{1_ns, CrystalId{1}, 511.0_keV}));
  std::array<Single, 4> out{};
  p::StreamDecoder d{ScannerGeometry::num_crystals};
  EXPECT_EQ(d.decode(words, out), 4U);
  EXPECT_EQ(d.stats().words, 4U);
}

TEST(StreamDecoder, LittleEndianBytes) {
  const std::uint64_t w = p::encode(Single{7_ns, CrystalId{18431}, 662.0_keV});
  std::array<std::byte, 12> bytes{};
  for (std::size_t i = 0; i < 8; ++i) {
    bytes[i] = static_cast<std::byte>((w >> (8 * i)) & 0xFFU);
  }
  std::array<Single, 2> out{};
  p::StreamDecoder d{ScannerGeometry::num_crystals};
  ASSERT_EQ(d.decode_bytes(bytes, out), 1U);
  EXPECT_EQ(out[0].crystal, CrystalId{18431});
  EXPECT_EQ(out[0].energy, 662.0_keV);
  EXPECT_EQ(d.truncated_bytes(), 4U);
}
