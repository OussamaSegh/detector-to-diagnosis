// SPDX-License-Identifier: MIT
// MiniDAQ - adapters for the ports (Chapter 6): a simulated detector and a
// counting sink. Chapter 9 adds a UDP detector, Chapter 12 a list-mode file
// sink; the core does not change. A product build (MINIDAQ_WITH_SIMULATOR
// off, CR-0029) has no simulated detector and refuses the synthetic source.
#pragma once

#include <atomic>
#include <memory>
#include <string>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/build.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/control/signing.hpp"

namespace minidaq::control {

// Counts what it receives and throws it away (a stand-in for the file writer).
class CountingSink final : public CoincidenceSinkPort {
 public:
  void write(std::span<const Coincidence> batch) override {
    coincidences_.fetch_add(batch.size(), std::memory_order_relaxed);
    batches_.fetch_add(1, std::memory_order_relaxed);
  }
  [[nodiscard]] std::string describe() const override { return "counting sink (discards data)"; }
  [[nodiscard]] std::uint64_t coincidences() const noexcept { return coincidences_.load(std::memory_order_relaxed); }
  [[nodiscard]] std::uint64_t batches() const noexcept { return batches_.load(std::memory_order_relaxed); }

 private:
  std::atomic<std::uint64_t> coincidences_{0};
  std::atomic<std::uint64_t> batches_{0};
};

// The production choice of adapters: the simulated detector or the UDP
// readout (Chapter 9) by source type, and the counting sink or the list-mode
// file sink (Chapter 12) by output type.
[[nodiscard]] std::unique_ptr<DetectorPort> make_default_detector(const config::AcquisitionConfig& c,
                                                                  std::string& error);
[[nodiscard]] std::unique_ptr<CoincidenceSinkPort> make_default_sink(const config::AcquisitionConfig& c,
                                                                     std::string& error);
// `o` with any missing detector or sink factory set to the defaults above. With a signing key,
// the list-mode sink signs each run's record (release 1.3.0, ADR 0034).
[[nodiscard]] ServiceOptions with_default_adapters(
    ServiceOptions o = {}, std::shared_ptr<const signing::SigningKey> run_key = nullptr);

}  // namespace minidaq::control
