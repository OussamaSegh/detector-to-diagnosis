// SPDX-License-Identifier: MIT
#include "minidaq/control/hardware.hpp"

#include <chrono>
#include <fstream>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/hw/mmio_bus.hpp"

namespace minidaq::control {

namespace {

std::int64_t steady_ns() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

hw::BoardFault parse_fault(const std::string& f) {
  if (f == "unresponsive") {
    return hw::BoardFault::unresponsive;
  }
  if (f == "vanished") {
    return hw::BoardFault::vanished;
  }
  if (f == "weak_supply") {
    return hw::BoardFault::weak_supply;
  }
  return hw::BoardFault::none;
}

}  // namespace

Expected<std::unique_ptr<SlowControlHardware>, std::string> SlowControlHardware::open(
    const config::HardwareConfig& cfg) {
  std::unique_ptr<SlowControlHardware> h{new SlowControlHardware};
  std::vector<hw::RegisterBus*> buses;
  for (const config::BoardConfig& b : cfg.boards) {
    if (cfg.backend == "mmio") {
      auto bus = hw::MmioBus::open(b.device, b.size, b.offset);
      if (!bus) {
        return Unexpected{bus.error()};
      }
      h->buses_.push_back(std::move(*bus));
    } else {
      auto board = std::make_unique<hw::FakeBoard>(static_cast<std::uint8_t>(b.slot), steady_ns);
      board->set_temperature(b.temperature_c);
      board->set_dark_current_ua(b.dark_current_ua);
      board->set_fault(parse_fault(b.fault));
      h->simulated_.push_back({board.get(), b.temperature_file});
      h->buses_.push_back(std::move(board));
    }
    buses.push_back(h->buses_.back().get());
  }
  h->describe_ = std::to_string(cfg.boards.size()) +
                 (cfg.boards.size() == 1 ? " board, " : " boards, ") + cfg.backend;
  h->sc_ = std::make_unique<hw::SlowControl>(cfg.settings, std::move(buses));
  SlowControlHardware* self = h.get();
  h->sc_->start(steady_ns, [self] { self->update_simulation(); });
  return h;
}

SlowControlHardware::~SlowControlHardware() {
  sc_->stop();
  sc_->power_down();  // the fail-safe state of a SiPM is unbiased
}

// A simulated board whose temperature follows a file: one number in degrees Celsius. A file that
// is missing or does not hold a number leaves the temperature as it was.
void SlowControlHardware::update_simulation() {
  for (const Simulated& s : simulated_) {
    if (s.temperature_file.empty()) {
      continue;
    }
    std::ifstream in{s.temperature_file};
    std::string text;
    if (in >> text) {
      if (const auto t = parse_number<double>(text, -40.0, 125.0)) {
        s.board->set_temperature(*t);
      }
    }
  }
}

std::vector<HardwareBoard> SlowControlHardware::boards() const {
  std::vector<HardwareBoard> out;
  for (const hw::BoardSnapshot& b : sc_->snapshot()) {
    out.push_back(HardwareBoard{b.slot, hw::to_string(b.state), hw::to_string(b.temp_level),
                                b.temperature_c, b.target_mv / 1000.0, b.setpoint_mv / 1000.0,
                                b.monitor_mv / 1000.0, b.current_ua, b.at_limit, b.fault});
  }
  return out;
}

}  // namespace minidaq::control
