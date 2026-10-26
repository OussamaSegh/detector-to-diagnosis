// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 21.2. The starter passes the first three, fails the fourth and dies
// on the last: that is the crash from the field.
#include <gtest/gtest.h>

#include <string>

#include "group_parser.hpp"

using ex21::parse_groups;

TEST(GroupParser, CountsGroupsAndDepth) {
  const auto r = parse_groups("{ {a} {b {c}} } {}");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_EQ(r.groups, 5U);
  EXPECT_EQ(r.depth, 3U);
}

TEST(GroupParser, RejectsUnbalancedBraces) {
  EXPECT_NE(parse_groups("{a}}").error.find("'}' without '{' at byte 3"), std::string::npos);
  EXPECT_FALSE(parse_groups("{{a}").ok);
  EXPECT_TRUE(parse_groups("no groups at all").ok);
}

TEST(GroupParser, AcceptsTheDeepestNestingTheFormatAllows) {
  const std::string text = std::string(ex21::max_depth, '{') + std::string(ex21::max_depth, '}');
  const auto r = parse_groups(text);
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_EQ(r.depth, ex21::max_depth);
}

TEST(GroupParser, RejectsOneLevelMore) {
  const std::string text = std::string(ex21::max_depth + 1, '{') + std::string(ex21::max_depth + 1, '}');
  const auto r = parse_groups(text);
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("deeper than 64 at byte 64"), std::string::npos) << r.error;
}

TEST(GroupParser, TheFieldCaptureIsAnErrorNotACrash) {
  // The capture the site sent with its crash report: a configuration file whose generator looped,
  // 16,777,216 opening braces and nothing else. Built here instead of stored as a 16 MiB file.
  const std::string capture(std::size_t{1} << 24, '{');
  const auto r = parse_groups(capture);
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("deeper than 64"), std::string::npos) << r.error;
}
