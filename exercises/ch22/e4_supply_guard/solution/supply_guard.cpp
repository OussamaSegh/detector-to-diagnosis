// SPDX-License-Identifier: MIT
#include "supply_guard.hpp"

#include <array>
#include <cmath>
#include <cstdio>
#include <utility>

namespace exercise {

namespace {

const char* name(SupplyError e) { return e == SupplyError::timeout ? "timeout" : "refused"; }

// Runs an idempotent command up to `attempts` times; the last error, or empty on success.
template <typename Command>
std::optional<SupplyError> with_retries(int attempts, Command command) {
  std::optional<SupplyError> last;
  for (int i = 0; i < attempts; ++i) {
    last = command();
    if (!last) {
      return std::nullopt;
    }
  }
  return last;
}

std::string volts(double v) {
  std::array<char, 32> buf{};
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
  (void)std::snprintf(buf.data(), buf.size(), "%.3f V", v);
  return buf.data();
}

}  // namespace

bool SupplyGuard::turn_on(double v, std::int64_t now_ns) {
  if (state_ != GuardState::off) {
    return false;
  }
  if (auto e = with_retries(s_.max_attempts, [&] { return supply_.set_voltage(v); })) {
    enter_safe(std::string{"set_voltage: "} + name(*e));
    return false;
  }
  if (auto e = with_retries(s_.max_attempts, [&] { return supply_.set_output(true); })) {
    enter_safe(std::string{"set_output: "} + name(*e));
    return false;
  }
  target_v_ = v;
  deadline_ns_ = now_ns + s_.settle_ns;
  state_ = GuardState::ramping;
  return true;
}

void SupplyGuard::poll(std::int64_t now_ns) {
  if (state_ == GuardState::safe) {
    if (!off_confirmed_) {
      // The one command that matters now; idempotent, so it is safe to send every cycle.
      off_confirmed_ = !with_retries(s_.max_attempts, [&] { return supply_.set_output(false); });
    }
    return;
  }
  if (state_ != GuardState::ramping && state_ != GuardState::on) {
    return;
  }
  Supply::Reading r;
  for (int i = 0; i < s_.max_attempts; ++i) {
    r = supply_.read_voltage();
    if (!r.error) {
      break;
    }
  }
  if (r.error) {
    return enter_safe(std::string{"read_voltage: "} + name(*r.error));
  }
  const bool within = std::abs(r.volts - target_v_) <= s_.tolerance_v;
  if (within) {
    state_ = GuardState::on;
  } else if (state_ == GuardState::on) {
    enter_safe("lost the setpoint: " + volts(r.volts) + " measured, " + volts(target_v_) + " set");
  } else if (now_ns > deadline_ns_) {
    enter_safe("did not reach the setpoint in time: " + volts(r.volts) + " measured, " +
               volts(target_v_) + " set");
  }
}

bool SupplyGuard::acknowledge() {
  if (state_ != GuardState::safe || !off_confirmed_) {
    return false;  // a supply that may still be on is not re-armed
  }
  (void)supply_.clear_trip();  // once: a retry could clear a trip that happened in between
  state_ = GuardState::off;
  reason_.clear();
  off_confirmed_ = false;
  return true;
}

void SupplyGuard::enter_safe(std::string why) {
  if (state_ == GuardState::safe) {
    return;  // the first reason is the cause; later ones are consequences
  }
  state_ = GuardState::safe;
  reason_ = std::move(why);
  off_confirmed_ = !with_retries(s_.max_attempts, [&] { return supply_.set_output(false); });
}

}  // namespace exercise
