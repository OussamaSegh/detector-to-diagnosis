// SPDX-License-Identifier: MIT
#include "minidaq/hw/fake_board.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

#include "minidaq/hw/feb_regs.hpp"

namespace minidaq::hw {

namespace {

// The breakdown voltage the simulated SiPMs have, for the dark current only: the model of a
// Hamamatsu S14160-3050HS, 38 V at 25 C and 34 mV/C (its datasheet). The slow control has its own
// copy of these numbers in its settings, as it would for a real board.
constexpr double vbd_25c_mv = 38'000.0;
constexpr double vbd_mv_per_c = 34.0;

}  // namespace

FakeBoard::FakeBoard(std::uint8_t slot, Clock clock)
    : clock_{std::move(clock)},
      last_ns_{clock_()},
      slot_{slot},
      fw_version_{feb::FwVersion::reset} {
  soft_reset_locked();
}

void FakeBoard::soft_reset_locked() {
  control_ = feb::Control::reset;
  setpoint_mv_ = feb::BiasSetpoint::reset;
  ramp_mv_per_s_ = feb::BiasRampRate::reset;
  threshold_ = feb::Threshold::reset;
  errors_ = feb::ErrorFlags::reset;
  overtemp_ = false;
  fifo_words_ = 0;
}

// [snippet:fake-physics]
void FakeBoard::update_locked(std::int64_t now_ns) {
  const double dt_s = static_cast<double>(std::max<std::int64_t>(0, now_ns - last_ns_)) * 1e-9;
  last_ns_ = now_ns;
  if (temperature_c_ > overtemp_limit_c && !overtemp_) {
    overtemp_ = true;  // the board's own protection: bias off, a sticky flag
    control_ = feb::Control::BiasEnable::set(control_, 0);
    errors_ |= feb::ErrorFlags::OvertempTrip::mask;
  }
  const bool enabled = feb::Control::BiasEnable::get(control_) != 0;
  double target = enabled ? static_cast<double>(setpoint_mv_) : 0.0;
  if (enabled && fault_ == BoardFault::weak_supply && target > 30'000.0) {
    target *= 0.95;
  }
  // The supply moves at the programmed rate when it is on and discharges at the same rate
  // when it is off; a rate of 0 would never move, so the hardware treats it as 1 V/s.
  const double rate = ramp_mv_per_s_ == 0 ? 1'000.0 : static_cast<double>(ramp_mv_per_s_);
  const double step = rate * dt_s;
  if (std::abs(target - bias_mv_) <= step) {
    bias_mv_ = target;
  } else {
    bias_mv_ += target > bias_mv_ ? step : -step;
  }
  // The output FIFO: events in while the triggers are on, the link out; what does not fit is
  // lost, and the board says so in a sticky flag.
  const double in = feb::Control::TriggerEnable::get(control_) != 0 ? fill_words_per_s_ : 0.0;
  const double out = fault_ == BoardFault::stalled_link ? 0.0 : drain_words_per_s_;
  fifo_words_ += (in - out) * dt_s;
  if (fifo_words_ > fifo_depth_words) {
    fifo_words_ = fifo_depth_words;
    errors_ |= feb::ErrorFlags::FifoOverflow::mask;
  }
  fifo_words_ = std::max(0.0, fifo_words_);
}
// [/snippet:fake-physics]

std::uint32_t FakeBoard::status_locked() const {
  const bool enabled = feb::Control::BiasEnable::get(control_) != 0;
  const auto setpoint = static_cast<double>(setpoint_mv_);
  const bool at_setpoint = std::abs(bias_mv_ - setpoint) <= ready_band_mv;
  // A weak supply ramps like a good one and stalls at 95% of the setpoint; the board flags the
  // fault once the output has stopped short.
  const bool stalled = enabled && fault_ == BoardFault::weak_supply && setpoint > 30'000.0 &&
                       bias_mv_ >= setpoint * 0.95 - ready_band_mv;
  std::uint32_t s = 0;
  s = feb::Status::BiasReady::set(s, enabled && at_setpoint ? 1 : 0);
  s = feb::Status::BiasRamping::set(s, enabled && !at_setpoint && !stalled ? 1 : 0);
  s = feb::Status::Overtemp::set(s, overtemp_ ? 1 : 0);
  s = feb::Status::BiasFault::set(s, stalled ? 1 : 0);
  s = feb::Status::FifoEmpty::set(s, fifo_words_ < 1.0 ? 1 : 0);
  return s;
}

std::uint32_t FakeBoard::read_locked(std::uint32_t address) const {
  switch (address) {
    case feb::BoardId::address:
      return feb::BoardId::Slot::set(feb::BoardId::reset, slot_);
    case feb::FwVersion::address:
      return fw_version_;
    case feb::Control::address:
      return control_;  // SOFT_RESET reads as 0: it is never stored
    case feb::Status::address:
      return status_locked();
    case feb::ErrorFlags::address:
      return errors_;
    case feb::FifoLevel::address:
      return static_cast<std::uint32_t>(std::lround(std::min(fifo_words_, 65'535.0)));
    case feb::BiasSetpoint::address:
      return setpoint_mv_;
    case feb::BiasMonitor::address:
      return static_cast<std::uint32_t>(std::lround(std::max(0.0, bias_mv_)));
    case feb::BiasCurrent::address: {
      const double overvoltage_v =
          (bias_mv_ - (vbd_25c_mv + vbd_mv_per_c * (temperature_c_ - 25.0))) / 1000.0;
      // Dark current grows with the overvoltage and doubles every 8 C (a model, not a datasheet).
      const double ua = overvoltage_v <= 0 ? 0.0
                                           : dark_current_ua_ * (overvoltage_v / 2.7) *
                                                 std::exp2((temperature_c_ - 25.0) / 8.0);
      return static_cast<std::uint32_t>(std::lround(std::min(ua, 65'535.0)));
    }
    case feb::BiasRampRate::address:
      return ramp_mv_per_s_;
    case feb::Temperature::address: {
      const auto q7 = static_cast<std::int32_t>(std::lround(temperature_c_ * 128.0));
      return static_cast<std::uint32_t>(q7) & feb::Temperature::CelsiusQ7::mask;
    }
    case feb::Threshold::address:
      return threshold_;
    default:
      return 0;
  }
}

bool FakeBoard::hang_locked(std::unique_lock<std::mutex>& lock) {
  if (fault_ != BoardFault::hung_bus) {
    return false;
  }
  // A stuck bus holds the thread that accessed it, not the board: set_fault() still gets in.
  (void)fault_changed_.wait_for(lock, hang_time, [this] { return fault_ != BoardFault::hung_bus; });
  return true;
}

Expected<std::uint32_t, HwError> FakeBoard::read32(std::uint32_t address) {
  std::unique_lock lock{mu_};
  ++accesses_;
  if (address % 4 != 0 || address > feb::Threshold::address) {
    return Unexpected{HwError{HwErrc::bad_address, address}};
  }
  if (hang_locked(lock) || fault_ == BoardFault::unresponsive) {
    return Unexpected{HwError{HwErrc::timeout, address}};
  }
  if (fault_ == BoardFault::vanished) {
    return 0xFFFF'FFFFU;
  }
  update_locked(clock_());
  return read_locked(address);
}

HwStatus FakeBoard::write32(std::uint32_t address, std::uint32_t value) {
  std::unique_lock lock{mu_};
  ++accesses_;
  if (address % 4 != 0 || address > feb::Threshold::address) {
    return {HwError{HwErrc::bad_address, address}};
  }
  if (hang_locked(lock) || fault_ == BoardFault::unresponsive) {
    return {HwError{HwErrc::timeout, address}};
  }
  if (fault_ == BoardFault::vanished) {
    return {};  // posted writes to a device that has gone are lost without an error
  }
  update_locked(clock_());
  switch (address) {
    case feb::Control::address:
      if (feb::Control::SoftReset::get(value) != 0) {
        soft_reset_locked();
        break;
      }
      // The board keeps the bias off while it is too hot, whatever software writes.
      control_ = value & (feb::Control::BiasEnable::mask | feb::Control::TriggerEnable::mask);
      if (overtemp_) {
        control_ = feb::Control::BiasEnable::set(control_, 0);
      }
      break;
    case feb::ErrorFlags::address:
      errors_ &= ~value;  // write 1 to clear
      break;
    case feb::BiasSetpoint::address:
      setpoint_mv_ = feb::BiasSetpoint::Millivolts::set(0, value);
      break;
    case feb::BiasRampRate::address:
      ramp_mv_per_s_ = feb::BiasRampRate::MillivoltsPerS::set(0, value);
      break;
    case feb::Threshold::address:
      threshold_ = feb::Threshold::Code::set(0, value);
      break;
    default:
      break;  // writes to read-only registers have no effect on the board
  }
  return {};
}

void FakeBoard::set_temperature(double celsius) {
  const std::lock_guard lock{mu_};
  update_locked(clock_());
  temperature_c_ = celsius;
  if (overtemp_ && celsius < overtemp_limit_c - 5.0) {
    overtemp_ = false;  // the board re-arms 5 C below its limit; the sticky flag stays
  }
  update_locked(clock_());
}

void FakeBoard::set_fault(BoardFault f) {
  {
    const std::lock_guard lock{mu_};
    update_locked(clock_());
    fault_ = f;
  }
  fault_changed_.notify_all();
}

void FakeBoard::set_firmware(std::uint32_t fw_version) {
  const std::lock_guard lock{mu_};
  fw_version_ = fw_version;
}

void FakeBoard::set_data_rates(double fill_words_per_s, double drain_words_per_s) {
  const std::lock_guard lock{mu_};
  update_locked(clock_());
  fill_words_per_s_ = fill_words_per_s;
  drain_words_per_s_ = drain_words_per_s;
}

void FakeBoard::set_dark_current_ua(double ua) {
  const std::lock_guard lock{mu_};
  dark_current_ua_ = ua;
}

double FakeBoard::bias_volts() {
  const std::lock_guard lock{mu_};
  update_locked(clock_());
  return bias_mv_ / 1000.0;
}

std::uint64_t FakeBoard::accesses() const {
  const std::lock_guard lock{mu_};
  return accesses_;
}

}  // namespace minidaq::hw
