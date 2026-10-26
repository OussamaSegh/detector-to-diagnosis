// SPDX-License-Identifier: MIT
// MiniDAQ - the hardware port of the acquisition service, made of the slow control of
// Chapter 22 and the buses of a hardware description: memory-mapped boards or simulated ones.
//
// It owns the buses and the slow control's thread, which starts with it and runs until it is
// destroyed; destruction then switches every board's bias off.
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "minidaq/config/hardware_config.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/core/expected.hpp"
#include "minidaq/hw/fake_board.hpp"
#include "minidaq/hw/slow_control.hpp"

namespace minidaq::control {

class SlowControlHardware final : public HardwarePort {
 public:
  // Opens the boards of the description and starts the slow control.
  [[nodiscard]] static Expected<std::unique_ptr<SlowControlHardware>, std::string> open(
      const config::HardwareConfig& cfg);
  ~SlowControlHardware() override;
  SlowControlHardware(const SlowControlHardware&) = delete;
  SlowControlHardware& operator=(const SlowControlHardware&) = delete;
  SlowControlHardware(SlowControlHardware&&) = delete;
  SlowControlHardware& operator=(SlowControlHardware&&) = delete;

  [[nodiscard]] std::optional<std::string> not_ready() const override { return sc_->not_ready(); }
  [[nodiscard]] std::optional<std::string> fault() const override { return sc_->fault(); }
  void acknowledge() override { sc_->acknowledge(); }
  [[nodiscard]] std::vector<HardwareBoard> boards() const override;
  [[nodiscard]] std::string describe() const override { return describe_; }

 private:
  SlowControlHardware() = default;
  struct Simulated {
    hw::FakeBoard* board;
    std::string temperature_file;
  };
  void update_simulation();

  std::vector<std::unique_ptr<hw::RegisterBus>> buses_;
  std::vector<Simulated> simulated_;
  std::unique_ptr<hw::SlowControl> sc_;
  std::string describe_;
};

}  // namespace minidaq::control
