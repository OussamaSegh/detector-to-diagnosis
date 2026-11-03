// SPDX-License-Identifier: MIT
// The slow control of the front-end boards against simulated boards (Chapter 22). Time is a
// variable the test moves, so a ramp of forty seconds takes no time at all.
#include <gtest/gtest.h>

#include <chrono>
#include <cstdint>
#include <string>
#include <vector>

#include "eventually.hpp"
#include "minidaq/core/flight_recorder.hpp"
#include "minidaq/hw/fake_board.hpp"
#include "minidaq/hw/feb_regs.hpp"
#include "minidaq/hw/slow_control.hpp"
#include "traced.hpp"

using namespace minidaq;
using namespace minidaq::hw;

namespace {

constexpr std::int64_t ms = 1'000'000;
constexpr std::int64_t s = 1'000 * ms;

// A board, a slow control over it and the time they share.
struct Rig {
  std::int64_t now = 0;
  FakeBoard board{2, [this] { return now; }};
  SlowControl sc;
  explicit Rig(SlowControlSettings settings = {}) : sc{settings, {&board}} {}
  // Cycles every 100 ms for the given time.
  void run_for(std::int64_t duration_ns) {
    const std::int64_t end = now + duration_ns;
    while (now < end) {
      sc.step(now);
      now += 100 * ms;
    }
    sc.step(now);
  }
  [[nodiscard]] BoardSnapshot state() const { return sc.snapshot().at(0); }
};

// Forwards to a board and records the writes, in order.
class WriteLog final : public RegisterBus {
 public:
  explicit WriteLog(RegisterBus& inner) : inner_{inner} {}
  std::vector<std::uint32_t> writes;  // addresses
  Expected<std::uint32_t, HwError> read32(std::uint32_t a) override { return inner_.read32(a); }
  HwStatus write32(std::uint32_t a, std::uint32_t v) override {
    writes.push_back(a);
    return inner_.write32(a, v);
  }

 private:
  RegisterBus& inner_;
};

// A board whose bias monitor reads 0 whatever the supply does: a broken readback.
class DeadMonitor final : public RegisterBus {
 public:
  explicit DeadMonitor(RegisterBus& inner) : inner_{inner} {}
  Expected<std::uint32_t, HwError> read32(std::uint32_t a) override {
    if (a == feb::BiasMonitor::address) {
      return 0U;
    }
    return inner_.read32(a);
  }
  HwStatus write32(std::uint32_t a, std::uint32_t v) override { return inner_.write32(a, v); }

 private:
  RegisterBus& inner_;
};

// A board that reports extra bits in its status and error flags: its own protection found
// something that the slow control's own readings do not show.
class Raised final : public RegisterBus {
 public:
  Raised(RegisterBus& inner, std::uint32_t status, std::uint32_t errors)
      : inner_{inner}, status_{status}, errors_{errors} {}
  Expected<std::uint32_t, HwError> read32(std::uint32_t a) override {
    auto v = inner_.read32(a);
    if (v && a == feb::Status::address) {
      return *v | status_;
    }
    if (v && a == feb::ErrorFlags::address) {
      return *v | errors_;
    }
    return v;
  }
  HwStatus write32(std::uint32_t a, std::uint32_t v) override { return inner_.write32(a, v); }

 private:
  RegisterBus& inner_;
  std::uint32_t status_;
  std::uint32_t errors_;
};

// A board on which writes to one register fail while `refuse` is set, as on a bus that loses
// some transactions.
class RefusedWrites final : public RegisterBus {
 public:
  RefusedWrites(RegisterBus& inner, std::uint32_t address) : inner_{inner}, address_{address} {}
  bool refuse = true;
  Expected<std::uint32_t, HwError> read32(std::uint32_t a) override { return inner_.read32(a); }
  HwStatus write32(std::uint32_t a, std::uint32_t v) override {
    if (refuse && a == address_) {
      return HwStatus{HwError{HwErrc::bus_error, a}};
    }
    return inner_.write32(a, v);
  }

 private:
  RegisterBus& inner_;
  std::uint32_t address_;
};

}  // namespace

TEST(SlowControl, KeepsTheOvervoltageConstantAsTheTemperatureMoves) {
  // REQ: SRS-HW-001
  Rig rig;
  rig.run_for(45 * s);  // 0 to 40.7 V at 1 V/s
  auto st = rig.state();
  ASSERT_EQ(st.state, BoardState::ready) << st.fault;
  EXPECT_EQ(st.slot, 2U);
  EXPECT_DOUBLE_EQ(st.target_mv, 40'700.0) << "38 V + 2.7 V at 25 C";
  EXPECT_NEAR(rig.board.bias_volts(), 40.7, 0.001);

  rig.board.set_temperature(30.0);  // V_bd rises by 5 x 34 mV
  rig.run_for(2 * s);
  st = rig.state();
  EXPECT_DOUBLE_EQ(st.setpoint_mv, 40'870.0);
  EXPECT_EQ(st.state, BoardState::ready);
  EXPECT_NEAR(rig.board.bias_volts(), 40.87, 0.001);

  rig.board.set_temperature(30.1);  // 3.4 mV: below the update step, nothing is written
  rig.run_for(1 * s);
  EXPECT_DOUBLE_EQ(rig.state().setpoint_mv, 40'870.0);
  rig.board.set_temperature(30.2);  // 6.8 mV
  rig.run_for(1 * s);
  EXPECT_DOUBLE_EQ(rig.state().setpoint_mv, 40'877.0);
}

TEST(SlowControl, NeverSetsABiasOutsideItsLimits) {
  // REQ: SRS-HW-001
  SlowControlSettings settings;
  settings.bias_max_mv = 40'900.0;
  Rig rig{settings};
  rig.board.set_temperature(34.0);  // wants 41.006 V
  rig.run_for(45 * s);
  const auto st = rig.state();
  EXPECT_DOUBLE_EQ(st.target_mv, 41'006.0);
  EXPECT_DOUBLE_EQ(st.setpoint_mv, 40'900.0);
  EXPECT_TRUE(st.at_limit);
  EXPECT_EQ(st.state, BoardState::ready);
}

TEST(SlowControl, WritesTheRampRateAndTheSetpointBeforeItEnablesTheSupply) {
  // REQ: SRS-HW-002
  Rig base;
  WriteLog log{base.board};
  SlowControl sc{{}, {&log}};
  sc.step(0);
  const std::vector<std::uint32_t> expected{feb::BiasRampRate::address, feb::BiasSetpoint::address,
                                            feb::Control::address};
  EXPECT_EQ(log.writes, expected);
  EXPECT_EQ(*read<feb::BiasRampRate>(base.board), 1'000U);
  EXPECT_EQ(sc.snapshot().at(0).state, BoardState::ramping);
  sc.step(100 * ms);
  EXPECT_EQ(log.writes.size(), 3U) << "a setpoint is written again only when it changes";
}

TEST(SlowControl, WarnsWithHysteresisAndSwitchesTheBiasOffAtTheAlarm) {
  // REQ: SRS-HW-003
  Rig rig;
  rig.run_for(45 * s);
  rig.board.set_temperature(35.0);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().temp_level, TempLevel::warning);
  rig.board.set_temperature(34.5);  // inside the hysteresis: still a warning
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().temp_level, TempLevel::warning);
  rig.board.set_temperature(33.9);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().temp_level, TempLevel::normal);
  EXPECT_EQ(rig.state().state, BoardState::ready) << "a warning alone does not stop the board";

  rig.board.set_temperature(40.0);
  rig.run_for(100 * ms);
  const auto st = rig.state();
  EXPECT_EQ(st.state, BoardState::fault);
  EXPECT_EQ(st.temp_level, TempLevel::alarm);
  EXPECT_EQ(st.fault, "temperature 40.00 C is at or above the alarm limit 40.0 C");
  EXPECT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 0U) << "fail-safe: unbiased";
  rig.run_for(45 * s);
  EXPECT_DOUBLE_EQ(rig.board.bias_volts(), 0.0);
  rig.board.set_temperature(25.0);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().state, BoardState::fault) << "latched until acknowledged";
  EXPECT_DOUBLE_EQ(rig.state().temperature_c, 25.0) << "the display still follows the sensor";
}

TEST(SlowControl, DoesNotBelieveATemperatureBelowItsMinimum) {
  // REQ: SRS-HW-003
  Rig rig;
  rig.board.set_temperature(-0.5);  // a broken sensor reads like a freezing detector
  rig.run_for(100 * ms);
  EXPECT_EQ(rig.state().state, BoardState::fault);
  EXPECT_EQ(rig.state().fault, "temperature -0.50 C is below 5.0 C: the sensor is not believed");
}

TEST(SlowControl, LatchesAFaultForEachWayABoardFails) {
  // REQ: SRS-HW-004
  {
    Rig rig;
    rig.run_for(45 * s);
    rig.board.set_fault(BoardFault::unresponsive);
    rig.sc.step(rig.now);
    rig.sc.step(rig.now);
    EXPECT_EQ(rig.state().state, BoardState::ready) << "two failed cycles are tolerated";
    rig.sc.step(rig.now);
    EXPECT_EQ(rig.state().fault, "no answer in 3 cycles (timeout at 0x000)");
    EXPECT_EQ(rig.state().failed_accesses, 3U);
  }
  {
    Rig rig;
    rig.board.set_fault(BoardFault::vanished);
    rig.sc.step(0);
    EXPECT_EQ(
        rig.state().fault,
        "board identity 0xFFFFFFFF is not a front-end board (all ones: the device may have gone)");
  }
  {
    Rig rig;
    rig.board.set_fault(BoardFault::weak_supply);
    rig.run_for(45 * s);
    EXPECT_EQ(rig.state().fault,
              "the bias supply cannot hold the setpoint: 38.665 V measured, 40.700 V set");
    EXPECT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 0U);
  }
  {
    Rig rig;
    rig.board.set_dark_current_ua(600.0);
    rig.run_for(45 * s);
    EXPECT_EQ(rig.state().state, BoardState::fault);
    EXPECT_EQ(rig.state().fault.rfind("bias current ", 0), 0U) << rig.state().fault;
  }
  {
    std::int64_t now = 0;
    FakeBoard board{0, [&] { return now; }};
    DeadMonitor dead{board};
    SlowControl sc{{}, {&dead}};
    for (; now <= 42'600 * ms; now += 100 * ms) {
      sc.step(now);
    }
    EXPECT_EQ(sc.snapshot().at(0).state, BoardState::ramping) << "40.7 s of ramp and 2 s of grace";
    sc.step(42'800 * ms);
    EXPECT_EQ(sc.snapshot().at(0).fault,
              "the bias did not reach the setpoint in time: 0.000 V measured, 40.700 V set");
  }
}

TEST(SlowControl, LatchesTheBoardsOwnOvertemperatureAndOvercurrentFindings) {
  // REQ: SRS-HW-004
  // The board's protection acts on its own sensors; the slow control latches a fault whenever
  // the board says so, even at a temperature and a current that it finds normal itself. Found
  // untested by the release coverage review of 0.5.0.
  struct Case {
    std::uint32_t status;
    std::uint32_t errors;
    HwFaultCause cause;
  };
  for (const Case c : {Case{feb::Status::Overtemp::mask, 0, HwFaultCause::board_overtemp},
                       Case{0, feb::ErrorFlags::OvertempTrip::mask, HwFaultCause::board_overtemp},
                       Case{0, feb::ErrorFlags::Overcurrent::mask, HwFaultCause::overcurrent}}) {
    const std::uint64_t began = test_support::trace_clock_ns();
    std::int64_t now = 0;
    FakeBoard board{0, [&] { return now; }};
    Raised raised{board, c.status, c.errors};
    SlowControl sc{{}, {&raised}};
    sc.step(now);
    EXPECT_EQ(sc.snapshot().at(0).state, BoardState::fault) << static_cast<int>(c.cause);
    EXPECT_EQ(sc.snapshot().at(0).fault.rfind("the board switched its bias off for ", 0), 0U)
        << sc.snapshot().at(0).fault;
    const auto events = test_support::traced_since(began, TraceCode::hw_fault);
    ASSERT_EQ(events.size(), 1U);
    EXPECT_EQ(events[0].b, static_cast<std::uint64_t>(c.cause));
    EXPECT_EQ(*read_field<feb::Control::BiasEnable>(board), 0U) << "the bias is off";
  }
}

TEST(SlowControl, LeavesItsFaultInTheFlightRecorder) {
  // REQ: SRS-HW-004
  const std::uint64_t began = test_support::trace_clock_ns();
  Rig rig;
  rig.board.set_temperature(41.0);
  rig.sc.step(0);
  const auto events = test_support::traced_since(began, TraceCode::hw_fault);
  ASSERT_EQ(events.size(), 1U);
  EXPECT_EQ(events[0].a, 0U) << "board index";
  EXPECT_EQ(events[0].b, static_cast<std::uint64_t>(HwFaultCause::temperature));
}

TEST(SlowControl, AnAcknowledgedFaultClearsOnlyWhenItsCauseHasGone) {
  // REQ: SRS-HW-005
  Rig rig;
  rig.board.set_temperature(61.0);  // the board trips its own protection, sticky flag included
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().state, BoardState::fault);
  rig.sc.acknowledge();
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().state, BoardState::fault) << "still hot: the fault latches again";

  rig.board.set_temperature(25.0);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().state, BoardState::fault) << "nobody acknowledged";
  rig.sc.acknowledge();
  EXPECT_EQ(rig.sc.fault(), std::nullopt) << "an acknowledged fault is not reported again";
  EXPECT_EQ(rig.sc.not_ready(), "an acknowledgment waits for the next cycle");
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().state, BoardState::ramping) << rig.state().fault;
  EXPECT_EQ(*read<feb::ErrorFlags>(rig.board), 0U) << "the board's sticky flag was cleared";
  rig.run_for(45 * s);
  EXPECT_EQ(rig.state().state, BoardState::ready);
}

TEST(SlowControl, SaysWhyAnAcquisitionMayNotStart) {
  // REQ: SRS-HW-006
  Rig rig;
  EXPECT_EQ(rig.sc.not_ready(), "the slow control has not run yet");
  rig.sc.step(0);
  EXPECT_EQ(rig.sc.not_ready(), "board 0 (slot 2) is ramping");
  rig.run_for(45 * s);
  EXPECT_EQ(rig.sc.not_ready(), std::nullopt);
  EXPECT_EQ(rig.sc.fault(), std::nullopt);
  rig.board.set_temperature(45.0);
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.sc.fault(),
            "board 0 (slot 2): temperature 45.00 C is at or above the alarm limit 40.0 C");
  EXPECT_EQ(rig.sc.not_ready(), rig.sc.fault());
}

TEST(SlowControl, RunsItsOwnCycleOnAThreadUntilStopped) {
  // REQ: SRS-HW-001
  FakeBoard board{0, [] { return std::chrono::steady_clock::now().time_since_epoch().count(); }};
  SlowControlSettings settings;
  settings.period = std::chrono::milliseconds{1};
  SlowControl sc{settings, {&board}};
  sc.start([] { return std::chrono::steady_clock::now().time_since_epoch().count(); });
  EXPECT_TRUE(test_support::eventually([&] { return sc.cycles() >= 3; }));
  EXPECT_EQ(sc.snapshot().at(0).state, BoardState::ramping);
  sc.stop();
  const auto cycles = sc.cycles();
  const auto accesses = board.accesses();
  sc.stop();  // idempotent
  EXPECT_EQ(sc.cycles(), cycles);
  EXPECT_EQ(board.accesses(), accesses);
}

TEST(SlowControl, PowersEveryBoardDownAtShutdown) {
  // REQ: SRS-HW-004
  Rig rig;
  rig.run_for(45 * s);
  ASSERT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 1U);
  rig.sc.power_down();
  EXPECT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 0U);
  rig.now += 41 * s;
  EXPECT_DOUBLE_EQ(rig.board.bias_volts(), 0.0);
}

// Chapter 24: the firmware, the triggers and the output FIFO.

TEST(SlowControl, RefusesFirmwareItWasNotWrittenFor) {
  // REQ: SRS-HW-011
  for (const std::uint32_t ok : {0x0102'0000U, 0x0102'0011U, 0x0109'0001U}) {
    Rig rig;
    rig.board.set_firmware(ok);
    rig.run_for(45 * s);
    EXPECT_EQ(rig.state().state, BoardState::ready) << std::hex << ok;
  }
  const std::uint64_t began = test_support::trace_clock_ns();
  for (const std::uint32_t bad : {0x0101'0003U, 0x0200'0000U, 0x0002'0000U}) {
    Rig rig;
    rig.board.set_firmware(bad);
    rig.sc.step(0);
    EXPECT_EQ(rig.state().state, BoardState::fault) << std::hex << bad;
    EXPECT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 0U);
  }
  const auto events = test_support::traced_since(began, TraceCode::hw_fault);
  ASSERT_EQ(events.size(), 3U);
  EXPECT_EQ(events[0].b, static_cast<std::uint64_t>(HwFaultCause::firmware));

  // Checked every cycle: a board reflashed under a running system is caught at once, and an
  // acknowledgment does not clear it while the firmware stays.
  Rig rig;
  rig.run_for(45 * s);
  ASSERT_EQ(rig.state().state, BoardState::ready);
  EXPECT_EQ(rig.state().firmware, "1.2.0");
  rig.board.set_firmware(0x0101'0003U);
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().fault,
            "firmware 1.1.3 is not supported: this software needs 1.2 or a later 1.x");
  rig.sc.acknowledge();
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().state, BoardState::fault);
}

TEST(SlowControl, SwitchesTheTriggersWhenAskedAndSaysWhenItHasDone) {
  // REQ: SRS-HW-012, SRS-HW-013
  Rig rig;
  rig.run_for(45 * s);
  EXPECT_TRUE(rig.sc.triggers_are(false));
  EXPECT_EQ(*read_field<feb::Control::TriggerEnable>(rig.board), 0U);
  rig.sc.set_triggers(true);
  EXPECT_FALSE(rig.sc.triggers_are(true)) << "not before a cycle has done it";
  rig.sc.step(rig.now);
  EXPECT_TRUE(rig.sc.triggers_are(true));
  EXPECT_EQ(*read_field<feb::Control::TriggerEnable>(rig.board), 1U);
  EXPECT_EQ(*read_field<feb::Control::BiasEnable>(rig.board), 1U) << "the bias is left alone";
  EXPECT_FALSE(rig.sc.drained());

  rig.sc.set_triggers(false);
  rig.sc.step(rig.now);
  EXPECT_EQ(*read_field<feb::Control::TriggerEnable>(rig.board), 0U);
  EXPECT_FALSE(rig.sc.drained())
      << "the FIFO was read before the triggers went off: what it holds now is not known";
  rig.sc.step(rig.now);
  EXPECT_TRUE(rig.sc.drained());
}

TEST(SlowControl, SaysDrainedOnlyOnceTheFifoIsEmpty) {
  // REQ: SRS-HW-013
  Rig rig;
  rig.run_for(45 * s);
  rig.board.set_data_rates(20'000.0, 10'000.0);  // the FIFO fills at 10,000 words/s
  rig.sc.set_triggers(true);
  rig.sc.step(rig.now);
  rig.now += 100 * ms;
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().fifo_words, 1'000U);
  EXPECT_FALSE(rig.state().fifo_empty);

  rig.sc.set_triggers(false);
  rig.sc.step(rig.now);
  rig.now += 50 * ms;  // half of it sent
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().fifo_words, 500U);
  EXPECT_FALSE(rig.sc.drained());
  rig.now += 60 * ms;
  rig.sc.step(rig.now);
  EXPECT_TRUE(rig.sc.drained());
  EXPECT_EQ(rig.state().fifo_overflows, 0U);
}

TEST(SlowControl, CountsFifoOverflowsAsLostDataNotAsAFault) {
  // REQ: SRS-HW-015
  Rig rig;
  rig.run_for(45 * s);
  rig.board.set_data_rates(100'000.0, 50'000.0);  // full after 82 ms
  rig.sc.set_triggers(true);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().state, BoardState::ready);
  EXPECT_EQ(rig.state().fifo_words, 4'096U);
  const auto overflows = rig.state().fifo_overflows;
  EXPECT_GE(overflows, 9U) << "every cycle from the first full one finds the flag set again";
  EXPECT_EQ(*read_field<feb::ErrorFlags::FifoOverflow>(rig.board), 0U) << "the cycle cleared it";
  rig.now += 1 * ms;
  EXPECT_EQ(*read_field<feb::ErrorFlags::FifoOverflow>(rig.board), 1U)
      << "and the board sets it again when the next event finds the FIFO full";

  // The next run starts at zero: what overflowed before its triggers went on is not its loss.
  rig.sc.set_triggers(false);
  rig.run_for(1 * s);
  EXPECT_TRUE(rig.sc.drained());
  rig.board.set_data_rates(20'000.0, 1'000'000.0);
  rig.sc.set_triggers(true);
  rig.run_for(1 * s);
  EXPECT_EQ(rig.state().fifo_overflows, 0U);
}

TEST(SlowControl, ALatchedFaultSwitchesTheBiasAndTheTriggersOff) {
  // REQ: SRS-HW-004
  Rig rig;
  rig.run_for(45 * s);
  rig.sc.set_triggers(true);
  rig.sc.step(rig.now);
  ASSERT_EQ(*read_field<feb::Control::TriggerEnable>(rig.board), 1U);
  rig.board.set_temperature(41.0);
  rig.sc.step(rig.now);
  EXPECT_EQ(rig.state().state, BoardState::fault);
  EXPECT_EQ(*read<feb::Control>(rig.board), 0U);
  EXPECT_FALSE(rig.state().triggers);
  EXPECT_FALSE(rig.sc.triggers_are(true));
  EXPECT_FALSE(rig.sc.drained()) << "a board in fault cannot say what it still holds";
}

TEST(SlowControl, AFailedWriteIsAFailedAccessAndNeverEnablesTheBiasEarly) {
  // REQ: SRS-HW-002, SRS-HW-004
  // The write paths that the release coverage review of 0.5.0 found untested.
  {
    // The setpoint cannot be written: the supply is never enabled, and the cycles with a failed
    // access end in a fault.
    std::int64_t now = 0;
    FakeBoard board{0, [&] { return now; }};
    RefusedWrites bus{board, feb::BiasSetpoint::address};
    SlowControl sc{{}, {&bus}};
    sc.step(now);
    EXPECT_EQ(sc.snapshot().at(0).failed_accesses, 1U);
    EXPECT_EQ(*read_field<feb::Control::BiasEnable>(board), 0U) << "no enable without a setpoint";
    sc.step(now);
    sc.step(now);
    EXPECT_EQ(sc.snapshot().at(0).state, BoardState::fault);
    EXPECT_EQ(*read_field<feb::Control::BiasEnable>(board), 0U);
  }
  {
    // A new setpoint that cannot be written, and then can: one failed access, then the update.
    std::int64_t now = 0;
    FakeBoard board{0, [&] { return now; }};
    RefusedWrites bus{board, feb::BiasSetpoint::address};
    bus.refuse = false;
    SlowControl sc{{}, {&bus}};
    for (; now <= 45 * s; now += 100 * ms) {
      sc.step(now);
    }
    ASSERT_EQ(sc.snapshot().at(0).state, BoardState::ready);
    bus.refuse = true;
    board.set_temperature(30.0);  // a new setpoint is due
    sc.step(now);
    EXPECT_EQ(sc.snapshot().at(0).failed_accesses, 1U);
    bus.refuse = false;
    sc.step(now);
    EXPECT_EQ(sc.snapshot().at(0).failed_accesses, 1U);
    EXPECT_NE(sc.snapshot().at(0).state, BoardState::fault) << "one failed cycle is tolerated";
    EXPECT_GT(*read<feb::BiasSetpoint>(board), 40'700U) << "the new setpoint was written";
  }
  {
    // The triggers cannot be switched on: the slow control does not say they are.
    std::int64_t now = 0;
    FakeBoard board{0, [&] { return now; }};
    RefusedWrites bus{board, feb::Control::address};
    bus.refuse = false;
    SlowControl sc{{}, {&bus}};
    for (; now <= 45 * s; now += 100 * ms) {
      sc.step(now);
    }
    bus.refuse = true;
    sc.set_triggers(true);
    sc.step(now);
    EXPECT_FALSE(sc.triggers_are(true));
    EXPECT_EQ(sc.snapshot().at(0).failed_accesses, 1U);
    EXPECT_EQ(*read_field<feb::Control::TriggerEnable>(board), 0U);
  }
}
