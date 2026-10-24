// SPDX-License-Identifier: MIT
// MiniDAQ - adapters for the ports (Chapter 6): a simulated detector and a
// counting sink. Chapter 9 adds a UDP detector, Chapter 12 a list-mode file
// sink; the core does not change.
#pragma once

#include <atomic>
#include <memory>
#include <string>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/ports.hpp"
#include "minidaq/sim/paced_source.hpp"

namespace minidaq::control {

// Synthetic singles delivered at the configured rate, with due times.
class SimulatedDetector final : public DetectorPort {
 public:
  explicit SimulatedDetector(const config::SourceSettings& s);
  std::size_t read(std::span<std::uint64_t> out) override { return source_(out); }
  [[nodiscard]] std::function<std::int64_t(std::uint64_t)> due_times() override {
    return [this](std::uint64_t i) { return source_.due_ns(i); };
  }
  [[nodiscard]] std::string describe() const override { return description_; }

 private:
  sim::PacedSource source_;
  std::string description_;
};

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

// The production choice of adapters (today: simulated detector, counting sink).
[[nodiscard]] std::unique_ptr<DetectorPort> make_default_detector(const config::AcquisitionConfig& c,
                                                                  std::string& error);
[[nodiscard]] std::unique_ptr<CoincidenceSinkPort> make_default_sink(const config::AcquisitionConfig& c,
                                                                     std::string& error);
// `o` with any missing detector or sink factory set to the defaults above.
[[nodiscard]] ServiceOptions with_default_adapters(ServiceOptions o = {});

}  // namespace minidaq::control
