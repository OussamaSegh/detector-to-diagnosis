// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <bit>
#include <cstring>
#include <limits>

#include "minidaq/format/raw_single.hpp"

using namespace minidaq;
using namespace minidaq::literals;

TEST(Raw16, RoundTrip) {
  // REQ: SRS-FMT-001
  const Single s{123456789_ps, CrystalId{18000}, 511.0_keV};
  const auto bytes = serialize_raw16(s);
  const auto parsed = parse_single(bytes);
  ASSERT_TRUE(parsed) << to_string(parsed.error());
  EXPECT_EQ(*parsed, s);
}

TEST(Raw16, RejectsMalformedInput) {
  // REQ: SRS-FMT-002
  const Single good{1_ns, CrystalId{5}, 511.0_keV};
  auto make = [&](auto mutate) {
    auto b = serialize_raw16(good);
    mutate(b);
    return b;
  };
  auto set_u32 = [](std::array<std::byte, 16>& b, std::size_t off, std::uint32_t v) {
    std::memcpy(b.data() + off, &v, 4);
  };
  auto set_f32 = [&](std::array<std::byte, 16>& b, float f) {
    set_u32(b, 12, std::bit_cast<std::uint32_t>(f));
  };

  const std::array<std::byte, 16> full = serialize_raw16(good);
  EXPECT_EQ(parse_single(std::span(full).first(0)).error(), ParseError::truncated);
  EXPECT_EQ(parse_single(std::span(full).first(15)).error(), ParseError::truncated);
  EXPECT_EQ(parse_single(make([](auto& b) { b[7] = std::byte{0x80}; })).error(),
            ParseError::negative_time);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_u32(b, 8, 18432); })).error(),
            ParseError::crystal_out_of_range);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_u32(b, 8, 0xFFFFFFFF); })).error(),
            ParseError::crystal_out_of_range);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_f32(b, std::numeric_limits<float>::quiet_NaN()); }))
                .error(),
            ParseError::energy_not_finite);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_f32(b, std::numeric_limits<float>::infinity()); }))
                .error(),
            ParseError::energy_not_finite);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_f32(b, -1.0F); })).error(),
            ParseError::energy_out_of_range);
  EXPECT_EQ(parse_single(make([&](auto& b) { set_f32(b, 2000.5F); })).error(),
            ParseError::energy_out_of_range);
}

TEST(Raw16, ToStringCoversAllErrors) {
  for (auto e : {ParseError::truncated, ParseError::negative_time, ParseError::crystal_out_of_range,
                 ParseError::energy_not_finite, ParseError::energy_out_of_range}) {
    EXPECT_NE(to_string(e), "unknown");
  }
}
