// SPDX-License-Identifier: MIT
// MiniDAQ - a simulated front-end board behind the RegisterBus interface (Chapter 22).
//
// The board of hw/feb.toml as a program: its registers with their access rules (read-only,
// write-1-to-clear, a self-clearing reset bit), a bias supply that ramps towards its setpoint at
// the programmed rate, a temperature that a test or a scenario sets, the board's own protection
// (it switches the bias off above 60 C), and the faults a real board has: it stops answering,
// it answers all ones like a PCIe device that has gone, its supply cannot hold the setpoint, its
// bus hangs (an access that does not return).
// Since Chapter 24 it also has an output FIFO: while its triggers are on, events fill it at one
// rate and the data link empties it at another, and a full FIFO loses data (FIFO_OVERFLOW).
//
// Time is a function the owner gives, so a test moves it by hand and the server uses the steady
// clock. The board brings its state up to that time at every access. Thread-safe.
#pragma once

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>

#include "minidaq/hw/register.hpp"

namespace minidaq::hw {

enum class BoardFault : std::uint8_t {
  none,
  unresponsive,  // every access times out
  vanished,      // reads return 0xFFFFFFFF, writes are lost (a PCIe device that has gone)
  weak_supply,   // the bias stops 5% short of a setpoint above 30 V and the board flags bias_fault
  stalled_link,  // the data link sends nothing: the output FIFO never empties
  hung_bus,      // an access does not return for a minute, then times out (Chapter 25)
};

class FakeBoard final : public RegisterBus {
 public:
  using Clock = std::function<std::int64_t()>;  // nanoseconds, monotonic
  FakeBoard(std::uint8_t slot, Clock clock);

  [[nodiscard]] Expected<std::uint32_t, HwError> read32(std::uint32_t address) override;
  HwStatus write32(std::uint32_t address, std::uint32_t value) override;

  // The scenario's side: what the board's sensors see and which fault it has.
  void set_temperature(double celsius);
  void set_fault(BoardFault f);
  void set_dark_current_ua(double ua);          // at 2.7 V overvoltage and 25 C; scales with both
  void set_firmware(std::uint32_t fw_version);  // the FW_VERSION register; reset 1.2.0
  // Words per second that events put into the output FIFO while the triggers are on, and that
  // the data link takes out of it.
  void set_data_rates(double fill_words_per_s, double drain_words_per_s);
  // The bias the supply really outputs now, in volts, for tests.
  [[nodiscard]] double bias_volts();
  // Accesses so far (reads and writes, refused ones included).
  [[nodiscard]] std::uint64_t accesses() const;

  static constexpr double overtemp_limit_c = 60.0;
  static constexpr double ready_band_mv = 50.0;
  static constexpr double fifo_depth_words = 4'096.0;
  static constexpr std::chrono::seconds hang_time{60};

 private:
  void update_locked(std::int64_t now_ns);
  [[nodiscard]] std::uint32_t read_locked(std::uint32_t address) const;
  [[nodiscard]] std::uint32_t status_locked() const;
  void soft_reset_locked();
  // With hung_bus, waits until hang_time has passed or the fault has changed; true if it hung.
  bool hang_locked(std::unique_lock<std::mutex>& lock);

  mutable std::mutex mu_;
  std::condition_variable fault_changed_;
  Clock clock_;
  std::int64_t last_ns_;
  std::uint8_t slot_;
  BoardFault fault_ = BoardFault::none;
  // Registers that hold what software wrote.
  std::uint32_t control_ = 0;
  std::uint32_t setpoint_mv_ = 0;
  std::uint32_t ramp_mv_per_s_ = 0;
  std::uint32_t threshold_ = 0;
  std::uint32_t errors_ = 0;
  // The physics.
  double bias_mv_ = 0;
  double temperature_c_ = 25.0;
  double dark_current_ua_ = 2.0;
  bool overtemp_ = false;
  std::uint32_t fw_version_;
  double fill_words_per_s_ = 20'000.0;
  double drain_words_per_s_ = 1'000'000.0;
  double fifo_words_ = 0;
  std::uint64_t accesses_ = 0;
};

}  // namespace minidaq::hw
