// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 22.4: the guard against a scripted supply.
#include <gtest/gtest.h>

#include <deque>
#include <string>

#include "supply_guard.hpp"

using namespace exercise;

namespace {

constexpr std::int64_t s = 1'000'000'000;

// A supply whose next answers a test scripts. Each command takes its next error from its queue
// (empty queue: success). The output ramps to the voltage instantly unless `reaches` is set.
class ScriptedSupply final : public Supply {
 public:
  std::deque<std::optional<SupplyError>> set_voltage_errors, set_output_errors, read_errors;
  std::optional<double> reaches;  // where the output really goes when on (empty: the setpoint)
  int set_voltage_calls = 0, set_output_calls = 0, clear_trip_calls = 0, read_calls = 0;
  bool output_on = false;
  double setpoint = 0;

  std::optional<SupplyError> set_voltage(double v) override {
    ++set_voltage_calls;
    if (auto e = next(set_voltage_errors)) {
      return e;
    }
    setpoint = v;
    return std::nullopt;
  }
  std::optional<SupplyError> set_output(bool on) override {
    ++set_output_calls;
    if (auto e = next(set_output_errors)) {
      return e;
    }
    output_on = on;
    return std::nullopt;
  }
  std::optional<SupplyError> clear_trip() override {
    ++clear_trip_calls;
    return std::nullopt;
  }
  Reading read_voltage() override {
    ++read_calls;
    if (auto e = next(read_errors)) {
      return {e, 0};
    }
    return {std::nullopt, output_on ? reaches.value_or(setpoint) : 0.0};
  }

 private:
  static std::optional<SupplyError> next(std::deque<std::optional<SupplyError>>& q) {
    if (q.empty()) {
      return std::nullopt;
    }
    auto e = q.front();
    q.pop_front();
    return e;
  }
};

constexpr auto T = SupplyError::timeout;
constexpr auto R = SupplyError::refused;

}  // namespace

TEST(SupplyGuard, TurnsOnAndConfirmsTheOutput) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  EXPECT_EQ(g.state(), GuardState::ramping);
  EXPECT_DOUBLE_EQ(supply.setpoint, 40.7);
  EXPECT_TRUE(supply.output_on);
  g.poll(100'000'000);
  EXPECT_EQ(g.state(), GuardState::on);
  EXPECT_FALSE(g.turn_on(40.0, 0)) << "only from off";
}

TEST(SupplyGuard, RetriesAnIdempotentCommandAFewTimes) {
  ScriptedSupply supply;
  supply.set_voltage_errors = {T, R};
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  EXPECT_EQ(supply.set_voltage_calls, 3);
  supply.read_errors = {T, T};
  g.poll(1);
  EXPECT_EQ(g.state(), GuardState::on);
  EXPECT_EQ(supply.read_calls, 3);
}

TEST(SupplyGuard, GivesUpAfterItsAttemptsAndSwitchesTheOutputOff) {
  ScriptedSupply supply;
  supply.set_output_errors = {T, T, T};
  SupplyGuard g{supply, {}};
  EXPECT_FALSE(g.turn_on(40.7, 0));
  EXPECT_EQ(g.state(), GuardState::safe);
  EXPECT_EQ(g.reason(), "set_output: timeout");
  EXPECT_EQ(supply.set_output_calls, 4) << "three to switch on, then one to switch off";
  EXPECT_TRUE(g.off_confirmed());
  EXPECT_FALSE(supply.output_on);
}

TEST(SupplyGuard, ASupplyThatStopsAnsweringEndsInTheSafeState) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  g.poll(1);
  ASSERT_EQ(g.state(), GuardState::on);
  supply.read_errors = {T, T, T};
  g.poll(2);
  EXPECT_EQ(g.state(), GuardState::safe);
  EXPECT_EQ(g.reason(), "read_voltage: timeout");
  EXPECT_FALSE(supply.output_on);
}

TEST(SupplyGuard, ASupplyThatDoesNotReachItsSetpointFailsAtTheDeadline) {
  ScriptedSupply supply;
  supply.reaches = 38.665;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  g.poll(4 * s);
  EXPECT_EQ(g.state(), GuardState::ramping) << "late is not yet never";
  g.poll(5 * s);
  EXPECT_EQ(g.state(), GuardState::ramping) << "the deadline itself is still in time";
  g.poll(5 * s + 1);
  EXPECT_EQ(g.state(), GuardState::safe);
  EXPECT_EQ(g.reason(), "did not reach the setpoint in time: 38.665 V measured, 40.700 V set");
}

TEST(SupplyGuard, ASupplyThatLosesItsSetpointFailsAtOnce) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  g.poll(1);
  supply.reaches = 40.5;
  g.poll(2);
  EXPECT_EQ(g.state(), GuardState::safe);
  EXPECT_EQ(g.reason(), "lost the setpoint: 40.500 V measured, 40.700 V set");
}

TEST(SupplyGuard, KeepsTheFirstReason) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  supply.read_errors = {R, R, R};
  g.poll(1);
  g.poll(2);
  EXPECT_EQ(g.reason(), "read_voltage: refused");
}

TEST(SupplyGuard, KeepsTryingToSwitchOffAndWillNotRearmUntilItIsConfirmed) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  ASSERT_TRUE(g.turn_on(40.7, 0));
  g.poll(1);
  supply.read_errors = {T, T, T};
  supply.set_output_errors = {T, T, T, T, T, T};  // the switch-off fails in two calls
  g.poll(2);
  EXPECT_EQ(g.state(), GuardState::safe);
  EXPECT_FALSE(g.off_confirmed()) << "the guard does not claim what it does not know";
  EXPECT_FALSE(g.acknowledge());
  const int reads = supply.read_calls;
  g.poll(3);
  EXPECT_FALSE(g.off_confirmed());
  EXPECT_EQ(supply.read_calls, reads) << "in the safe state only the switch-off matters";
  g.poll(4);
  EXPECT_TRUE(g.off_confirmed());
  EXPECT_FALSE(supply.output_on);
  const int calls = supply.set_output_calls;
  g.poll(5);
  EXPECT_EQ(supply.set_output_calls, calls) << "confirmed once is enough";
}

TEST(SupplyGuard, AnAcknowledgmentClearsTheTripOnceAndReturnsToOff) {
  ScriptedSupply supply;
  SupplyGuard g{supply, {}};
  supply.set_voltage_errors = {T, T, T};
  ASSERT_FALSE(g.turn_on(40.7, 0));
  ASSERT_EQ(g.state(), GuardState::safe);
  EXPECT_FALSE(g.turn_on(40.7, 1)) << "not from the safe state";
  EXPECT_TRUE(g.acknowledge());
  EXPECT_EQ(supply.clear_trip_calls, 1);
  EXPECT_EQ(g.state(), GuardState::off);
  EXPECT_EQ(g.reason(), "");
  EXPECT_FALSE(g.acknowledge()) << "only from the safe state";
  EXPECT_EQ(supply.clear_trip_calls, 1);
  EXPECT_TRUE(g.turn_on(40.7, 2));
}
