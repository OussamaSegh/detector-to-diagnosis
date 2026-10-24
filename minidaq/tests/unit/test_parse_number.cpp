// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>

#include "minidaq/core/parse_number.hpp"

using minidaq::parse_number;

TEST(ParseNumber, AcceptsOnlyAWholeNumberInRange) {
  EXPECT_EQ(parse_number<int>("42"), 42);
  EXPECT_EQ(parse_number<int>("-7"), -7);
  EXPECT_EQ(parse_number<std::uint16_t>("7700"), 7700);
  EXPECT_EQ(parse_number<std::uint16_t>("65535"), 65535);
  EXPECT_FALSE(parse_number<std::uint16_t>("65536")) << "atoi would wrap this to port 0";
  EXPECT_FALSE(parse_number<std::uint16_t>("-1"));
  EXPECT_FALSE(parse_number<int>("7OO")) << "atoi would return 7";
  EXPECT_FALSE(parse_number<int>("abc")) << "atoi would return 0";
  EXPECT_FALSE(parse_number<int>(""));
  EXPECT_FALSE(parse_number<int>(" 1")) << "no leading space";
  EXPECT_FALSE(parse_number<int>("1 ")) << "no trailing text";
  EXPECT_FALSE(parse_number<int>("+1")) << "from_chars does not accept a plus sign";
}

TEST(ParseNumber, FloatingPointRejectsNonFiniteValues) {
  EXPECT_EQ(parse_number<double>("10e6"), 10e6);
  EXPECT_EQ(parse_number<double>("0.5"), 0.5);
  EXPECT_FALSE(parse_number<double>("inf"));
  EXPECT_FALSE(parse_number<double>("nan"));
  EXPECT_FALSE(parse_number<double>("1e999")) << "out of range for double";
  EXPECT_FALSE(parse_number<double>("1.5s"));
}

TEST(ParseNumber, BoundsAreInclusive) {
  EXPECT_EQ(parse_number<int>("1", 1, 3), 1);
  EXPECT_EQ(parse_number<int>("3", 1, 3), 3);
  EXPECT_FALSE(parse_number<int>("0", 1, 3));
  EXPECT_FALSE(parse_number<int>("4", 1, 3));
  EXPECT_FALSE(parse_number<double>("0", 1e-3, 1e3));
}
