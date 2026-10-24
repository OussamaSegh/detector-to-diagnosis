// SPDX-License-Identifier: MIT
// Exercise 6.5: a detector adapter that injects faults.
//
// Wraps any DetectorPort and, following a FaultPlan, makes it fail the way
// real readout fails: the link goes down, words arrive corrupted, the stream
// stalls, data arrives out of order. Because the service only knows the port,
// the whole fault handling of MiniDAQ can be tested without hardware.
#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "minidaq/control/ports.hpp"

namespace ex {

struct FaultPlan {
  // Report "link down after N words" from fault() once N words were delivered (0: never).
  std::uint64_t link_down_after_words = 0;
  // Replace the crystal id of every Nth word (the Nth, 2Nth, ...) with an invalid one (0: never).
  std::uint64_t corrupt_every = 0;
  // Once N words were delivered, deliver nothing for `stall_for` (0: never).
  std::uint64_t stall_after_words = 0;
  std::chrono::milliseconds stall_for{0};
  // Once N words were delivered, hold back the next read's words and deliver
  // them after `reorder_delay_words` further words (0: never).
  std::uint64_t reorder_after_words = 0;
  std::uint64_t reorder_delay_words = 10'000;
};

// What was injected, readable after the service has destroyed the detector.
struct FaultCounts {
  std::atomic<std::uint64_t> delivered{0};
  std::atomic<std::uint64_t> corrupted{0};
  std::atomic<std::uint64_t> stalls{0};
  std::atomic<std::uint64_t> reordered{0};
};

class FaultyDetector final : public minidaq::control::DetectorPort {
 public:
  FaultyDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan,
                 std::shared_ptr<FaultCounts> counts);
  std::size_t read(std::span<std::uint64_t> out) override;
  [[nodiscard]] std::function<std::int64_t(std::uint64_t)> due_times() override;
  [[nodiscard]] std::optional<std::string> fault() const override;
  [[nodiscard]] std::string describe() const override;

 private:
  std::unique_ptr<minidaq::control::DetectorPort> inner_;
  FaultPlan plan_;
  std::shared_ptr<FaultCounts> counts_;
  std::uint64_t delivered_ = 0;  // source thread only
  std::atomic<bool> link_down_{false};
  bool stalled_ = false;
  std::chrono::steady_clock::time_point stall_end_{};
  bool reordered_ = false;
  std::vector<std::uint64_t> held_;
  std::uint64_t release_at_ = 0;
};

// A factory that wraps whatever `inner` creates.
[[nodiscard]] minidaq::control::DetectorFactory faulty_factory(minidaq::control::DetectorFactory inner, FaultPlan plan,
                                                               std::shared_ptr<FaultCounts> counts);

}  // namespace ex
