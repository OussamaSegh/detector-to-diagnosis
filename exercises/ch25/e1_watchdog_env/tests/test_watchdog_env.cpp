// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 25.1: the watchdog settings systemd passes in the environment, and
// the notification messages a service sends back.
#include <gtest/gtest.h>

#include <chrono>

#include "watchdog_env.hpp"

using namespace sdwatch;
using std::chrono::microseconds;

TEST(WatchdogSettings, OffWithoutTheVariable) {
  EXPECT_EQ(watchdog_settings(nullptr, nullptr, 42).state, Watchdog::off);
  EXPECT_EQ(watchdog_settings(nullptr, "42", 42).state, Watchdog::off);
}

TEST(WatchdogSettings, OnPingsTwicePerInterval) {
  const auto s = watchdog_settings("10000000", nullptr, 42);
  EXPECT_EQ(s.state, Watchdog::on);
  EXPECT_EQ(s.interval, microseconds{10'000'000});
  EXPECT_EQ(s.ping_every, microseconds{5'000'000});
  EXPECT_EQ(watchdog_settings("3", nullptr, 42).ping_every, microseconds{1});
}

TEST(WatchdogSettings, OnlyForTheProcessItNames) {
  EXPECT_EQ(watchdog_settings("10000000", "42", 42).state, Watchdog::on);
  EXPECT_EQ(watchdog_settings("10000000", "43", 42).state, Watchdog::off);
}

TEST(WatchdogSettings, MalformedValuesAreInvalidNotGuessed) {
  for (const char* bad :
       {"", "0", "-5", "+5", " 5", "5 ", "5s", "1e6", "0x10", "99999999999999999999999"}) {
    EXPECT_EQ(watchdog_settings(bad, nullptr, 42).state, Watchdog::invalid) << '"' << bad << '"';
  }
  for (const char* bad : {"", "0", "-42", "42x", "99999999999999999999999"}) {
    EXPECT_EQ(watchdog_settings("10000000", bad, 42).state, Watchdog::invalid)
        << "WATCHDOG_PID \"" << bad << '"';
  }
}

TEST(Notification, SplitsAssignmentsInOrder) {
  const auto n = parse_notification("READY=1\nSTATUS=state idle\n");
  ASSERT_TRUE(n.has_value());
  ASSERT_EQ(n->size(), 2U);
  EXPECT_EQ((*n)[0], (std::pair<std::string, std::string>{"READY", "1"}));
  EXPECT_EQ((*n)[1], (std::pair<std::string, std::string>{"STATUS", "state idle"}));
}

TEST(Notification, ValuesMayBeEmptyOrHoldEqualsSigns) {
  const auto n = parse_notification("STATUS=\nERRNO=5\n\nX_1=a=b");
  ASSERT_TRUE(n.has_value());
  ASSERT_EQ(n->size(), 3U);
  EXPECT_EQ((*n)[0].second, "");
  EXPECT_EQ((*n)[2], (std::pair<std::string, std::string>{"X_1", "a=b"}));
  EXPECT_TRUE(parse_notification("").has_value());
}

TEST(Notification, RefusesWhatIsNotAnAssignment) {
  for (const char* bad :
       {"READY", "=1", "ready=1", "READY =1", "READY=1\nWATCHDOG", "STATUS-X=1"}) {
    EXPECT_FALSE(parse_notification(bad).has_value()) << bad;
  }
}
