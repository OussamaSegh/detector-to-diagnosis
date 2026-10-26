// SPDX-License-Identifier: MIT
// Exercise 22.4: a guard around a bias supply that may stop answering.
#pragma once

#include <cstdint>
#include <optional>
#include <string>

namespace exercise {

enum class SupplyError { timeout, refused };

// A bias supply with a command interface. Every command can fail; none throws.
class Supply {
 public:
  virtual ~Supply() = default;
  virtual std::optional<SupplyError> set_voltage(double volts) = 0;  // idempotent
  virtual std::optional<SupplyError> set_output(bool on) = 0;        // idempotent
  virtual std::optional<SupplyError> clear_trip() = 0;               // NOT idempotent
  struct Reading {
    std::optional<SupplyError> error;
    double volts = 0;
  };
  virtual Reading read_voltage() = 0;  // idempotent
};

struct GuardSettings {
  int max_attempts = 3;                    // tries of one idempotent command within one call
  std::int64_t settle_ns = 5'000'000'000;  // from turn_on() to the output within tolerance
  double tolerance_v = 0.1;
};

enum class GuardState { off, ramping, on, safe };

class SupplyGuard {
 public:
  SupplyGuard(Supply& supply, GuardSettings settings) : supply_{supply}, s_{settings} {}

  bool turn_on(double volts, std::int64_t now_ns);
  void poll(std::int64_t now_ns);
  bool acknowledge();

  [[nodiscard]] GuardState state() const { return state_; }
  [[nodiscard]] const std::string& reason() const { return reason_; }
  [[nodiscard]] bool off_confirmed() const { return off_confirmed_; }

 private:
  void enter_safe(std::string why);

  Supply& supply_;
  GuardSettings s_;
  GuardState state_ = GuardState::off;
  double target_v_ = 0;
  std::int64_t deadline_ns_ = 0;
  std::string reason_;
  bool off_confirmed_ = false;
};

}  // namespace exercise
