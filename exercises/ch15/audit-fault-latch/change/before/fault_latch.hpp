// SPDX-License-Identifier: MIT
// Exercise 15.6 (A): the fault latch of one front-end board in the slow-control
// loop, a risk control of H-10 (RC-27). Each cycle reads the board's status
// and current and writes its bias setpoint; the latch decides whether the
// board must be switched off until an operator acknowledges the fault.
#pragma once

#include <cstdint>
#include <string>

namespace ex156 {

// What one slow-control cycle of a board saw.
struct Cycle {
  bool reads_ok = true;            // every register read of the cycle succeeded
  bool writes_ok = true;           // every register write of the cycle succeeded
  bool board_overcurrent = false;  // the board's own fast comparator switched its bias off
  std::uint32_t current_ua = 0;    // the bias current read this cycle (valid if reads_ok)
};

struct Limits {
  std::uint32_t max_current_ua = 500;
  int max_failed_cycles = 3;
};

class FaultLatch {
 public:
  explicit FaultLatch(Limits limits) : limits_{limits} {}

  void on_cycle(const Cycle& c) {
    if (latched_) {
      return;  // latched until acknowledged
    }
    if (c.reads_ok && c.current_ua > limits_.max_current_ua) {
      latch("bias current " + std::to_string(c.current_ua) + " uA is above the limit " +
            std::to_string(limits_.max_current_ua) + " uA");
    }
  }

  void acknowledge() {
    latched_ = false;
    reason_.clear();
  }

  [[nodiscard]] bool latched() const noexcept { return latched_; }
  [[nodiscard]] const std::string& reason() const noexcept { return reason_; }

 private:
  void latch(std::string why) {
    latched_ = true;
    reason_ = std::move(why);
  }

  Limits limits_;
  bool latched_ = false;
  std::string reason_;
};

}  // namespace ex156
