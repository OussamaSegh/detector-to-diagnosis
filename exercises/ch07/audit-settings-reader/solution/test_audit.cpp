// SPDX-License-Identifier: MIT
// Exercise 7.6 (A): tests of the agent's change to the settings reader.
#include <gtest/gtest.h>

#include <string>

#include "subject.hpp"

namespace {

std::string file_with(const std::string& version, const std::string& window) {
  return "schema_version = " + version + "\ncoincidence_window_ns = " + window + "\n";
}

TEST(Audit, ReadsAWindowInNanoseconds) {
  const auto s = ex76::read_settings(file_with("2.2", "4.5"));
  ASSERT_TRUE(s.has_value());
  EXPECT_DOUBLE_EQ(s->coincidence_window_ns, 4.5);
}

TEST(Audit, AVersion21FileGetsTheDefaultWindow) {
  const auto s = ex76::read_settings("schema_version = 2.1\n");
  ASSERT_TRUE(s.has_value());
  EXPECT_DOUBLE_EQ(s->coincidence_window_ns, 4.0);
}

TEST(Audit, AWindowOutsideItsRangeIsAnError) {
  for (const char* w : {"0", "-1", "100.5", "nan", "inf", "4ns", "", "four"}) {
    EXPECT_FALSE(ex76::read_settings(file_with("2.2", w)).has_value()) << w;
  }
}

// What fuzz_config found (this chapter): a number that does not fit in a double.
TEST(Audit, ANumberOutsideTheRangeOfDoubleIsAnErrorNotACrash) {
  for (const char* w : {"6e688", "1e400", "-1e400", "1e-400"}) {
    EXPECT_NO_THROW({ EXPECT_FALSE(ex76::read_settings(file_with("2.2", w)).has_value()) << w; })
        << w;
  }
}

TEST(Audit, EveryVersionButTheTwoSupportedOnesIsRefused) {
  for (const char* v : {"", "2.0", "2.3", "3.0", "2.2.0", "2.2 x"}) {
    const auto s = ex76::read_settings(file_with(v, "4"));
    EXPECT_FALSE(s.has_value()) << "'" << v << "'";
  }
  EXPECT_FALSE(ex76::read_settings("coincidence_window_ns = 4\n").has_value());
}

TEST(Audit, AnErrorNamesItsReason) {
  const auto s = ex76::read_settings(file_with("2.2", "1e400"));
  ASSERT_FALSE(s.has_value());
  EXPECT_NE(s.error().find("coincidence_window_ns"), std::string::npos) << s.error();
}

}  // namespace
