// SPDX-License-Identifier: MIT
#include "minidaq/hw/slow_control.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <condition_variable>
#include <cstdio>
#include <utility>

#include "minidaq/core/flight_recorder.hpp"
#include "minidaq/hw/feb_regs.hpp"

namespace minidaq::hw {

const char* to_string(BoardState s) noexcept {
  switch (s) {
    case BoardState::off:
      return "off";
    case BoardState::ramping:
      return "ramping";
    case BoardState::ready:
      return "ready";
    case BoardState::fault:
      return "fault";
  }
  return "unknown";
}

const char* to_string(TempLevel l) noexcept {
  switch (l) {
    case TempLevel::normal:
      return "normal";
    case TempLevel::warning:
      return "warning";
    case TempLevel::alarm:
      return "alarm";
  }
  return "unknown";
}

namespace {

// A number with `digits` decimals, for the messages of faults.
std::string fixed(double v, int digits) {
  std::array<char, 32> buf{};
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
  (void)std::snprintf(buf.data(), buf.size(), "%.*f", digits, v);
  return buf.data();
}

std::string where(const HwError& e) {
  std::array<char, 64> buf{};
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
  (void)std::snprintf(buf.data(), buf.size(), " (%s at 0x%03X)",
                      std::string{to_string(e.code)}.c_str(), static_cast<unsigned>(e.address));
  return buf.data();
}

}  // namespace

SlowControl::SlowControl(const SlowControlSettings& settings,
                         const std::vector<RegisterBus*>& boards)
    : settings_{settings} {
  boards_.reserve(boards.size());
  for (std::size_t i = 0; i < boards.size(); ++i) {
    Board b{boards[i], {}, false, 0, std::nullopt};
    b.s.index = i;
    boards_.push_back(std::move(b));
  }
  published_.reserve(boards_.size());
  for (const auto& b : boards_) {
    published_.push_back(b.s);
  }
}

SlowControl::~SlowControl() { stop(); }

void SlowControl::latch(Board& b, HwFaultCause cause, std::string why) {
  if (b.s.state == BoardState::fault) {
    return;
  }
  b.s.state = BoardState::fault;
  b.s.fault = std::move(why);
  b.configured = false;
  b.ready_deadline_ns.reset();
  trace(TraceCode::hw_fault, b.s.index, static_cast<std::uint64_t>(cause));
  // The fail-safe state of a SiPM is unbiased. Best effort: a board that does not answer
  // cannot be told, and its own protection is all that is left.
  (void)write_field<feb::Control::BiasEnable>(*b.bus, 0);
}

// [snippet:step-board]
void SlowControl::step_board(Board& b, std::int64_t now_ns) {
  auto& s = b.s;
  if (s.state == BoardState::fault) {
    if (auto t = read_field<feb::Temperature::CelsiusQ7>(*b.bus)) {
      s.temperature_c =
          feb::Temperature::CelsiusQ7::get_signed(*t) / 128.0;  // for the display only
    }
    return;
  }
  // Read everything first; one failed access makes the whole cycle of this board fail.
  std::optional<HwError> failed;
  auto rd = [&](std::uint32_t address) -> std::uint32_t {
    if (failed) {
      return 0;
    }
    auto v = b.bus->read32(address);
    if (!v) {
      failed = v.error();
      return 0;
    }
    return *v;
  };
  const std::uint32_t id = rd(feb::BoardId::address);
  const std::uint32_t temp = rd(feb::Temperature::address);
  const std::uint32_t status = rd(feb::Status::address);
  const std::uint32_t errors = rd(feb::ErrorFlags::address);
  const std::uint32_t monitor = rd(feb::BiasMonitor::address);
  const std::uint32_t current = rd(feb::BiasCurrent::address);
  if (failed) {
    ++s.failed_accesses;
    if (++b.consecutive_failures >= settings_.max_failed_cycles) {
      latch(b, HwFaultCause::no_answer,
            "no answer in " + std::to_string(b.consecutive_failures) + " cycles" + where(*failed));
    }
    return;
  }
  b.consecutive_failures = 0;
  if (feb::BoardId::Magic::get(id) != 0x4D51) {
    std::array<char, 96> buf{};
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg)
    (void)std::snprintf(buf.data(), buf.size(), "board identity 0x%08X is not a front-end board%s",
                        id, id == 0xFFFF'FFFFU ? " (all ones: the device may have gone)" : "");
    latch(b, HwFaultCause::identity, buf.data());
    return;
  }
  s.slot = feb::BoardId::Slot::get(id);
  s.temperature_c = feb::Temperature::CelsiusQ7::get_signed(temp) / 128.0;
  s.monitor_mv = feb::BiasMonitor::Millivolts::get(monitor);
  s.current_ua = feb::BiasCurrent::Microamps::get(current);

  // Temperature: a warning with hysteresis, an alarm that latches, a reading not believed.
  const double t = s.temperature_c;
  if (t < settings_.temp_min_c) {
    latch(b, HwFaultCause::temperature,
          "temperature " + fixed(t, 2) + " C is below " + fixed(settings_.temp_min_c, 1) +
              " C: the sensor is not believed");
    return;
  }
  if (t >= settings_.temp_alarm_c) {
    s.temp_level = TempLevel::alarm;
    latch(b, HwFaultCause::temperature,
          "temperature " + fixed(t, 2) + " C is at or above the alarm limit " +
              fixed(settings_.temp_alarm_c, 1) + " C");
    return;
  }
  if (t >= settings_.temp_warning_c) {
    s.temp_level = TempLevel::warning;
  } else if (t < settings_.temp_warning_c - settings_.temp_hysteresis_c) {
    s.temp_level = TempLevel::normal;
  }
  // The board's own findings.
  if (feb::Status::Overtemp::get(status) != 0 || feb::ErrorFlags::OvertempTrip::get(errors) != 0) {
    latch(b, HwFaultCause::board_overtemp, "the board switched its bias off for overtemperature");
    return;
  }
  if (feb::ErrorFlags::Overcurrent::get(errors) != 0 || s.current_ua > settings_.max_current_ua) {
    latch(b, HwFaultCause::overcurrent,
          "bias current " + fixed(s.current_ua, 0) + " uA is above the limit " +
              fixed(settings_.max_current_ua, 0) + " uA");
    return;
  }
  if (feb::Status::BiasFault::get(status) != 0) {
    latch(b, HwFaultCause::supply,
          "the bias supply cannot hold the setpoint: " + fixed(s.monitor_mv / 1000.0, 3) +
              " V measured, " + fixed(s.setpoint_mv / 1000.0, 3) + " V set");
    return;
  }

  // The bias for this temperature, inside the limits; the setpoint is written before the
  // supply is enabled, so that it never drives an old value.
  s.target_mv = settings_.law.bias_mv(t);
  const double wanted = std::clamp(s.target_mv, settings_.bias_min_mv, settings_.bias_max_mv);
  s.at_limit = wanted != s.target_mv;
  const auto code = static_cast<std::uint32_t>(std::lround(wanted));
  if (!b.configured) {
    const bool written = write<feb::BiasRampRate>(*b.bus, settings_.ramp_mv_per_s) &&
                         write<feb::BiasSetpoint>(*b.bus, code) &&
                         write_field<feb::Control::BiasEnable>(*b.bus, 1);
    if (!written) {
      ++s.failed_accesses;
      ++b.consecutive_failures;
      return;
    }
    b.configured = true;
    s.setpoint_mv = code;
  } else if (std::abs(wanted - s.setpoint_mv) >= settings_.update_step_mv) {
    if (!write<feb::BiasSetpoint>(*b.bus, code)) {
      ++s.failed_accesses;
      ++b.consecutive_failures;
      return;
    }
    s.setpoint_mv = code;
  }

  // Ready, ramping, or late: a supply that has not reached its setpoint by the time the ramp
  // needs plus a grace period has failed, whatever its status says.
  if (feb::Status::BiasReady::get(status) != 0 &&
      std::abs(s.monitor_mv - s.setpoint_mv) <= settings_.readback_tolerance_mv) {
    s.state = BoardState::ready;
    b.ready_deadline_ns.reset();
    return;
  }
  s.state = BoardState::ramping;
  if (!b.ready_deadline_ns) {
    const double ramp_s =
        std::abs(s.setpoint_mv - s.monitor_mv) / std::max(1.0, double(settings_.ramp_mv_per_s));
    b.ready_deadline_ns = now_ns + static_cast<std::int64_t>(ramp_s * 1e9) +
                          std::chrono::nanoseconds{settings_.readback_grace}.count();
  }
  if (now_ns > *b.ready_deadline_ns) {
    latch(b, HwFaultCause::not_reached,
          "the bias did not reach the setpoint in time: " + fixed(s.monitor_mv / 1000.0, 3) +
              " V measured, " + fixed(s.setpoint_mv / 1000.0, 3) + " V set");
  }
}
// [/snippet:step-board]

void SlowControl::step(std::int64_t now_ns) {
  if (const std::uint64_t ack = ack_requested_.load(); ack != ack_done_) {
    ack_done_ = ack;
    for (auto& b : boards_) {
      if (b.s.state == BoardState::fault) {
        b.s.state = BoardState::off;
        b.s.fault.clear();
        b.s.temp_level = TempLevel::normal;
        b.consecutive_failures = 0;
        b.ready_deadline_ns.reset();
        // Clear the board's sticky errors, or the next cycle would latch them again.
        (void)clear<feb::ErrorFlags>(
            *b.bus, feb::ErrorFlags::Overcurrent::mask | feb::ErrorFlags::OvertempTrip::mask);
      }
    }
  }
  for (auto& b : boards_) {
    step_board(b, now_ns);
  }
  cycles_.fetch_add(1, std::memory_order_relaxed);
  const std::lock_guard lock{mu_};
  for (std::size_t i = 0; i < boards_.size(); ++i) {
    published_[i] = boards_[i].s;
  }
  published_ack_ = ack_done_;
}

void SlowControl::start(Clock clock, std::function<void()> before_each) {
  stop();
  thread_ = std::jthread{[this, clock = std::move(clock),
                          before_each = std::move(before_each)](const std::stop_token& st) {
    std::mutex m;
    std::condition_variable_any cv;
    auto next = std::chrono::steady_clock::now();
    while (!st.stop_requested()) {
      if (before_each) {
        before_each();
      }
      step(clock());
      next += settings_.period;
      std::unique_lock lock{m};
      (void)cv.wait_until(lock, st, next, [] { return false; });  // wakes early only on stop
    }
  }};
}

void SlowControl::stop() {
  if (thread_.joinable()) {
    thread_.request_stop();
    thread_.join();
  }
}

void SlowControl::power_down() {
  for (auto& b : boards_) {
    (void)write_field<feb::Control::BiasEnable>(*b.bus, 0);
    b.configured = false;
  }
}

std::vector<BoardSnapshot> SlowControl::snapshot() const {
  const std::lock_guard lock{mu_};
  return published_;
}

std::optional<std::string> SlowControl::fault() const {
  const std::lock_guard lock{mu_};
  if (published_ack_ != ack_requested_.load()) {
    return std::nullopt;
  }
  for (const auto& s : published_) {
    if (s.state == BoardState::fault) {
      return "board " + std::to_string(s.index) + " (slot " + std::to_string(s.slot) +
             "): " + s.fault;
    }
  }
  return std::nullopt;
}

std::optional<std::string> SlowControl::not_ready() const {
  if (auto f = fault()) {
    return f;
  }
  const std::lock_guard lock{mu_};
  if (cycles_.load(std::memory_order_relaxed) == 0) {
    return std::string{"the slow control has not run yet"};
  }
  if (published_ack_ != ack_requested_.load()) {
    return std::string{"an acknowledgment waits for the next cycle"};
  }
  for (const auto& s : published_) {
    if (s.state != BoardState::ready) {
      return "board " + std::to_string(s.index) + " (slot " + std::to_string(s.slot) + ") is " +
             to_string(s.state);
    }
  }
  return std::nullopt;
}

void SlowControl::acknowledge() { ack_requested_.fetch_add(1); }

}  // namespace minidaq::hw
