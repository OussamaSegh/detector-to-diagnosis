#include <gtest/gtest.h>

#include <cstring>
#include <type_traits>

#include "status.hpp"

TEST(StructLayout, FitsIn24Bytes) {
  EXPECT_LE(sizeof(ex::DetectorStatus), 24U);
}

TEST(StructLayout, MembersKeepTheirTypes) {
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::temperature_c), float>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::singles_rate_hz), double>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::bias_on), bool>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::block_id), std::uint16_t>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::alarm), bool>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::bias_mv), std::uint32_t>));
  EXPECT_TRUE((std::is_same_v<decltype(ex::DetectorStatus::fw_revision), std::uint8_t>));
}

TEST(StructLayout, TriviallyCopyable) {
  ex::DetectorStatus a{};
  a.block_id = 71;
  a.singles_rate_hz = 412345.5;
  a.temperature_c = 24.5F;
  a.bias_mv = 29'500;
  a.bias_on = true;
  a.fw_revision = 3;
  ex::DetectorStatus b{};
  std::memcpy(&b, &a, sizeof a);
  EXPECT_EQ(b.block_id, 71);
  EXPECT_EQ(b.bias_mv, 29'500U);
  EXPECT_TRUE(std::is_trivially_copyable_v<ex::DetectorStatus>);
}
