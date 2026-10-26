// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 22.2.
#include <gtest/gtest.h>

#include <limits>

#include "bias_controller.hpp"

using namespace exercise;

TEST(BiasController, FollowsTheTemperatureToKeepTheOvervoltage) {
  BiasController c;
  auto d = c.step(25.0);
  EXPECT_TRUE(d.bias_on);
  EXPECT_DOUBLE_EQ(d.target_mv, 40'700.0);
  EXPECT_EQ(d.write_mv, 40'700.0) << "the first step writes";
  EXPECT_FALSE(d.at_limit);
  EXPECT_EQ(d.level, Level::normal);
  d = c.step(30.0);
  EXPECT_DOUBLE_EQ(d.target_mv, 40'870.0);
  EXPECT_EQ(d.write_mv, 40'870.0);
  d = c.step(20.0);
  EXPECT_EQ(d.write_mv, 40'530.0);
}

TEST(BiasController, WritesOnlyWhenTheBiasMovedByTheStep) {
  BiasController c;
  ASSERT_EQ(c.step(25.0).write_mv, 40'700.0);
  EXPECT_EQ(c.step(25.1).write_mv, std::nullopt) << "3.4 mV";
  EXPECT_EQ(c.step(25.13).write_mv, std::nullopt)
      << "4 mV from the last write, not from the last step";
  EXPECT_EQ(c.step(25.15).write_mv, 40'705.0) << "5.1 mV, rounded to a whole millivolt";
  EXPECT_EQ(c.step(25.0).write_mv, 40'700.0) << "down by 5 mV";
}

TEST(BiasController, StaysInsideItsLimits) {
  BiasSettings s;
  s.max_mv = 40'800.0;
  s.min_mv = 40'600.0;
  BiasController c{s};
  auto d = c.step(34.0);
  EXPECT_DOUBLE_EQ(d.target_mv, 40'800.0);
  EXPECT_TRUE(d.at_limit);
  EXPECT_EQ(d.write_mv, 40'800.0);
  d = c.step(10.0);
  EXPECT_DOUBLE_EQ(d.target_mv, 40'600.0);
  EXPECT_TRUE(d.at_limit);
  d = c.step(25.0);
  EXPECT_FALSE(d.at_limit);
}

TEST(BiasController, WarnsWithHysteresis) {
  BiasController c;
  EXPECT_EQ(c.step(34.9).level, Level::normal);
  EXPECT_EQ(c.step(35.0).level, Level::warning);
  EXPECT_EQ(c.step(34.5).level, Level::warning) << "inside the hysteresis";
  EXPECT_EQ(c.step(34.0).level, Level::warning) << "34.0 is not below 34.0";
  EXPECT_EQ(c.step(33.9).level, Level::normal);
  EXPECT_EQ(c.step(34.5).level, Level::normal) << "rising inside the hysteresis does not warn";
  EXPECT_TRUE(c.step(36.0).bias_on) << "a warning does not switch the bias off";
}

TEST(BiasController, AnAlarmLatchesUntilAcknowledged) {
  BiasController c;
  ASSERT_TRUE(c.step(25.0).bias_on);
  auto d = c.step(40.0);
  EXPECT_FALSE(d.bias_on);
  EXPECT_EQ(d.level, Level::alarm);
  EXPECT_EQ(d.write_mv, std::nullopt);
  EXPECT_TRUE(c.latched());
  d = c.step(25.0);
  EXPECT_FALSE(d.bias_on) << "cooling down does not clear the alarm";
  EXPECT_EQ(d.level, Level::alarm);
  c.acknowledge();
  EXPECT_FALSE(c.latched());
  d = c.step(25.0);
  EXPECT_TRUE(d.bias_on);
  EXPECT_EQ(d.write_mv, 40'700.0) << "after an acknowledgment the setpoint is written again";
}

TEST(BiasController, AnAcknowledgedAlarmWhoseCauseRemainsLatchesAgain) {
  BiasController c;
  (void)c.step(41.0);
  c.acknowledge();
  const auto d = c.step(41.0);
  EXPECT_FALSE(d.bias_on);
  EXPECT_TRUE(c.latched());
}

TEST(BiasController, DoesNotBelieveImpossibleReadings) {
  for (const double t : {std::numeric_limits<double>::quiet_NaN(), 4.9, -256.0}) {
    BiasController c;
    const auto d = c.step(t);
    EXPECT_FALSE(d.bias_on) << t;
    EXPECT_EQ(d.level, Level::invalid) << t;
    EXPECT_EQ(c.step(25.0).level, Level::invalid) << "latched: " << t;
  }
  BiasController c;
  EXPECT_TRUE(c.step(5.0).bias_on) << "the minimum itself is believed";
}
