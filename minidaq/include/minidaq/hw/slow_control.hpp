// SPDX-License-Identifier: MIT
// MiniDAQ - slow control of the front-end boards (Chapter 22).
//
// A SiPM's gain is proportional to its overvoltage, the bias above its breakdown voltage, and
// the breakdown voltage rises with temperature (34 mV/C for the SiPM this book models, at an
// overvoltage of 2.7 V: 1.3% of gain per degree). A detector whose temperature drifts by 5 C
// under a fixed bias moves its 511 keV photopeak by about 6%, and the energy window of the
// coincidence sorter then cuts a different share of the events. The slow control keeps the
// overvoltage constant: every cycle it reads each board's temperature and sets its bias to
// V_bd(T) + V_ov, inside fixed limits.
//
// It is also the part of the software that watches the hardware. It raises a warning, and above
// a second limit an alarm, for temperature; it compares the bias the board measures with the
// setpoint; it counts accesses that fail. Any of these that persists latches a fault on that
// board, switches its bias off when the board still answers (the fail-safe state of a SiPM is
// unbiased), and stays latched until an operator acknowledges it and the cause has gone. The
// acquisition service reads the faults and stops a run (fault source "hw").
//
// One thread writes the boards' state (the cycle, step()); any thread reads a copy of it.
#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "minidaq/hw/register.hpp"

namespace minidaq::hw {

// [snippet:settings]
struct BiasLaw {
  double vbd_25c_mv = 38'000.0;  // breakdown voltage at 25 C
  double vbd_mv_per_c = 34.0;    // its temperature coefficient
  double overvoltage_mv = 2'700.0;
  // The bias that keeps the overvoltage at temperature t.
  [[nodiscard]] double bias_mv(double t_c) const noexcept {
    return vbd_25c_mv + vbd_mv_per_c * (t_c - 25.0) + overvoltage_mv;
  }
};

struct SlowControlSettings {
  BiasLaw law;
  double bias_min_mv = 36'000.0;  // never set a bias outside these limits,
  double bias_max_mv = 43'000.0;  // whatever the temperature says
  std::uint32_t ramp_mv_per_s = 1'000;
  double update_step_mv = 5.0;  // write a new setpoint only when the target moved this much
  double temp_warning_c = 35.0;
  double temp_alarm_c = 40.0;  // fault: bias off
  double temp_hysteresis_c = 1.0;
  double temp_min_c = 5.0;  // below: the sensor is not believed (fault)
  double readback_tolerance_mv = 100.0;
  std::chrono::milliseconds readback_grace{2'000};  // beyond the ramp's own duration
  double max_current_ua = 500.0;
  int max_failed_cycles = 3;  // consecutive cycles with a failed access: fault
  std::chrono::milliseconds period{100};
};
// [/snippet:settings]

enum class BoardState : std::uint8_t { off, ramping, ready, fault };
// Why a board's fault latched; the flight recorder's hw_fault event carries it.
enum class HwFaultCause : std::uint8_t {
  no_answer = 1,
  identity,
  temperature,
  board_overtemp,
  overcurrent,
  supply,
  not_reached,
};
enum class TempLevel : std::uint8_t { normal, warning, alarm };
[[nodiscard]] const char* to_string(BoardState s) noexcept;
[[nodiscard]] const char* to_string(TempLevel l) noexcept;

struct BoardSnapshot {
  std::size_t index = 0;
  std::uint32_t slot = 0;
  BoardState state = BoardState::off;
  TempLevel temp_level = TempLevel::normal;
  double temperature_c = 0;
  double target_mv = 0;    // V_bd(T) + V_ov
  double setpoint_mv = 0;  // what the board was told, after the limits
  double monitor_mv = 0;   // what it measures
  double current_ua = 0;
  bool at_limit = false;  // the target was outside the limits
  std::string fault;      // empty unless state == fault
  std::uint64_t failed_accesses = 0;
};

class SlowControl {
 public:
  // The buses must outlive the SlowControl. Board i is boards[i].
  SlowControl(const SlowControlSettings& settings, const std::vector<RegisterBus*>& boards);
  ~SlowControl();
  SlowControl(const SlowControl&) = delete;
  SlowControl& operator=(const SlowControl&) = delete;
  SlowControl(SlowControl&&) = delete;
  SlowControl& operator=(SlowControl&&) = delete;

  // One cycle over every board, at time now_ns (monotonic). Tests call it directly.
  void step(std::int64_t now_ns);
  // A thread that calls step() every period until stop() or destruction; before_each, if
  // given, runs on that thread before every cycle (a simulation updates its sensors there).
  using Clock = std::function<std::int64_t()>;
  void start(Clock clock, std::function<void()> before_each = {});
  void stop();
  // Switches every board's bias off, best effort; for shutdown, after stop().
  void power_down();

  [[nodiscard]] std::vector<BoardSnapshot> snapshot() const;
  // The first board's fault, "board 1 (slot 3): ...", or empty. Empty too while an
  // acknowledgment waits for its cycle: the fault it acknowledged is not reported again.
  [[nodiscard]] std::optional<std::string> fault() const;
  // Why an acquisition may not start now (a board not ready, a fault, an acknowledgment not yet
  // processed), or empty.
  [[nodiscard]] std::optional<std::string> not_ready() const;
  // Asks the next cycle to clear every latched fault and power the board up again; a fault whose
  // cause remains latches again in that cycle.
  void acknowledge();
  [[nodiscard]] std::uint64_t cycles() const noexcept {
    return cycles_.load(std::memory_order_relaxed);
  }
  [[nodiscard]] const SlowControlSettings& settings() const noexcept { return settings_; }

 private:
  struct Board {
    RegisterBus* bus = nullptr;
    BoardSnapshot s;
    bool configured = false;  // ramp rate, setpoint and enable written since the last fault
    int consecutive_failures = 0;
    std::optional<std::int64_t> ready_deadline_ns;  // set when the board stops being ready
  };
  void step_board(Board& b, std::int64_t now_ns);
  void latch(Board& b, HwFaultCause cause, std::string why);

  SlowControlSettings settings_;
  std::vector<Board> boards_;  // the cycle's own state: only step() touches it
  mutable std::mutex mu_;
  std::vector<BoardSnapshot> published_;  // a copy for readers, under mu_
  std::uint64_t published_ack_ = 0;       // the acknowledgments that copy has seen, under mu_
  std::atomic<std::uint64_t> ack_requested_{0};
  std::uint64_t ack_done_ = 0;  // the cycle's own
  std::atomic<std::uint64_t> cycles_{0};
  std::jthread thread_;
};

}  // namespace minidaq::hw
