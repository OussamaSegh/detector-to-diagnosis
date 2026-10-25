// SPDX-License-Identifier: MIT
// Exercise 18.4: a detector port that wraps another and injects faults, so a
// test can make any detector fail in a planned way. A decorator, not a new
// fake: the words still come from the real (or simulated) device, and only the
// failure is scripted.
#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

#include "minidaq/control/ports.hpp"

namespace ex {

struct FaultPlan {
  // After this many words have been delivered, report `message` as a fault and
  // deliver nothing more. 0: never.
  std::uint64_t fault_after_words = 0;
  std::string message = "injected fault";
  // Drop every n-th word read from the inner port (counted). 0: never.
  std::uint64_t drop_every = 0;
  // Reads number [stall_from, stall_from + stall_reads) return 0 without
  // reading the inner port, as a device that stops sending for a while.
  std::uint64_t stall_from = 0;
  std::uint64_t stall_reads = 0;
};

class FaultInjectingDetector final : public minidaq::control::DetectorPort {
 public:
  FaultInjectingDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan);

  std::size_t read(std::span<std::uint64_t> out) override;
  [[nodiscard]] std::optional<std::string> fault() const override;
  [[nodiscard]] std::string describe() const override;
  // The inner port's counters, then "rejected_injected": the dropped words. The name
  // makes the run's integrity verdict count them as a loss (run_integrity.cpp).
  [[nodiscard]] std::vector<minidaq::control::DetectorCounter> counters() const override;

  [[nodiscard]] std::uint64_t delivered() const noexcept { return delivered_.load(); }

 private:
  std::unique_ptr<minidaq::control::DetectorPort> inner_;
  FaultPlan plan_;
  std::uint64_t reads_ = 0;  // source thread only
  std::uint64_t seen_ = 0;   // words read from the inner port, source thread only
  std::atomic<std::uint64_t> delivered_{0};
  std::atomic<std::uint64_t> dropped_{0};
  std::atomic<bool> faulted_{false};
};

}  // namespace ex
