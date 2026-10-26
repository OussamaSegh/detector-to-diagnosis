// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 22.3.
#include <gtest/gtest.h>

#include "tmp117.hpp"

using tmp117::decode_temperature;
using tmp117::is_tmp117;

TEST(Tmp117, DecodesPositiveTemperatures) {
  EXPECT_EQ(decode_temperature(0x0C, 0x80), 25.0);  // 3200 / 128
  EXPECT_EQ(decode_temperature(0x00, 0x00), 0.0);
  EXPECT_EQ(decode_temperature(0x00, 0x01), 0.0078125) << "one bit is 7.8125 mC";
  EXPECT_EQ(decode_temperature(0x12, 0xC0), 37.5);
}

TEST(Tmp117, DecodesNegativeTemperaturesAsTwosComplement) {
  EXPECT_EQ(decode_temperature(0xFF, 0x80), -1.0);
  EXPECT_EQ(decode_temperature(0xF3, 0x80), -25.0);
  EXPECT_EQ(decode_temperature(0xE5, 0x00), -54.0);
}

TEST(Tmp117, TheMostSignificantByteComesFirst) {
  EXPECT_EQ(decode_temperature(0x80, 0x0C), std::nullopt) << "0x800C is about -255.9 C, not 25 C";
  EXPECT_EQ(decode_temperature(0x01, 0x00), 2.0);
}

TEST(Tmp117, RefusesTheResetValueAndValuesOutsideItsRange) {
  EXPECT_EQ(decode_temperature(0x80, 0x00), std::nullopt) << "-256 C: no conversion yet";
  EXPECT_EQ(decode_temperature(0x80, 0x01), std::nullopt);
  EXPECT_EQ(decode_temperature(0xE4, 0x80), -55.0) << "the lower end of the range";
  EXPECT_EQ(decode_temperature(0xE4, 0x7F), std::nullopt);
  EXPECT_EQ(decode_temperature(0x4B, 0x00), 150.0) << "the upper end of the range";
  EXPECT_EQ(decode_temperature(0x4B, 0x01), std::nullopt);
  EXPECT_EQ(decode_temperature(0x7F, 0xFF), std::nullopt);
}

TEST(Tmp117, RecognizesItsDeviceIdWhateverTheRevision) {
  EXPECT_TRUE(is_tmp117(0x01, 0x17));
  EXPECT_TRUE(is_tmp117(0x11, 0x17)) << "revision 1";
  EXPECT_TRUE(is_tmp117(0xF1, 0x17));
  EXPECT_FALSE(is_tmp117(0x01, 0x16)) << "another device";
  EXPECT_FALSE(is_tmp117(0x17, 0x01)) << "the bytes the wrong way round";
  EXPECT_FALSE(is_tmp117(0xFF, 0xFF)) << "a bus with nothing on it";
  EXPECT_FALSE(is_tmp117(0x00, 0x00));
}
