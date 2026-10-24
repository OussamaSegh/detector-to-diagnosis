// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <chrono>

#include "duration.hpp"

using ex75::parse_duration;
using namespace std::chrono_literals;

TEST(Duration, AcceptsTheGrammar) {
  EXPECT_EQ(parse_duration("250ms"), 250ms);
  EXPECT_EQ(parse_duration("20us"), 20us);
  EXPECT_EQ(parse_duration("7ns"), 7ns);
  EXPECT_EQ(parse_duration("2s"), 2s);
  EXPECT_EQ(parse_duration("3min"), 3min);
  EXPECT_EQ(parse_duration("0s"), 0ns);
  EXPECT_EQ(parse_duration("007ms"), 7ms) << "leading zeros are digits";
}

TEST(Duration, FractionsAreExact) {
  EXPECT_EQ(parse_duration("1.5s"), 1500ms);
  EXPECT_EQ(parse_duration("0.1s"), 100ms);
  EXPECT_EQ(parse_duration("4.1s"), 4100ms) << "strtod and a multiplication give 4099999999.9999995 ns";
  EXPECT_EQ(parse_duration("0.000000001s"), 1ns);
  EXPECT_EQ(parse_duration("2.250us"), 2250ns);
  EXPECT_EQ(parse_duration("1.50ns"), std::nullopt) << "half a nanosecond";
  EXPECT_EQ(parse_duration("1.0ns"), 1ns) << "a zero below the nanosecond is fine";
  EXPECT_EQ(parse_duration("0.0000000001s"), std::nullopt);
}

TEST(Duration, RejectsWhatStrtodAccepts) {
  for (const char* bad : {"", "s", "10", "10 ms", " 10ms", "10ms ", "10MS", "10m", "10sec", "-5ms", "+5ms",
                          "1e3ms", "inf s", "nan", "0x10ms", ".5s", "1.s", "1..5s", "10ms10ms"}) {
    EXPECT_EQ(parse_duration(bad), std::nullopt) << '"' << bad << '"';
  }
}

TEST(Duration, RejectsOverflowInsteadOfWrapping) {
  // INT64_MAX ns is about 292 years.
  EXPECT_EQ(parse_duration("9223372036854775807ns"), std::chrono::nanoseconds{9223372036854775807});
  EXPECT_EQ(parse_duration("9223372036854775808ns"), std::nullopt);
  EXPECT_EQ(parse_duration("9223372036s"), std::chrono::nanoseconds{9223372036'000'000'000});
  EXPECT_EQ(parse_duration("9223372037s"), std::nullopt);
  EXPECT_EQ(parse_duration("153722868min"), std::nullopt);
  EXPECT_EQ(parse_duration("99999999999999999999999s"), std::nullopt);
}
