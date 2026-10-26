// SPDX-License-Identifier: MIT
// MiniDAQ - a simulated front-end board behind the RegisterBus interface (Chapter 22).
//
// The board of hw/feb.toml as a program: its registers with their access rules (read-only,
// write-1-to-clear, a self-clearing reset bit), a bias supply that ramps towards its setpoint at
// the programmed rate, a temperature that a test or a scenario sets, the board's own protection
// (it switches the bias off above 60 C), and the faults a real board has: it stops answering,
// it answers all ones like a PCIe device that has gone, its supply cannot hold the setpoint.
//
// Time is a function the owner gives, so a test moves it by hand and the server uses the steady
// clock. The board brings its state up to that time at every access. Thread-safe.
#pragma once

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
  void set_dark_current_ua(double ua);  // at 2.7 V overvoltage and 25 C; scales with both
  // The bias the supply really outputs now, in volts, for tests.
  [[nodiscard]] double bias_volts();
  // Accesses so far (reads and writes, refused ones included).
  [[nodiscard]] std::uint64_t accesses() const;

  static constexpr double overtemp_limit_c = 60.0;
  static constexpr double ready_band_mv = 50.0;

 private:
  void update_locked(std::int64_t now_ns);
  [[nodiscard]] std::uint32_t read_locked(std::uint32_t address) const;
  [[nodiscard]] std::uint32_t status_locked() const;
  void soft_reset_locked();

  mutable std::mutex mu_;
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
  std::uint64_t accesses_ = 0;
};

}  // namespace minidaq::hw
