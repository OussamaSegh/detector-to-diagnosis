// SPDX-License-Identifier: MIT
// Exercise 6.5 starter: a pass-through adapter. Make it misbehave on purpose.
#include "faulty_detector.hpp"

namespace ex {

FaultyDetector::FaultyDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan,
                               std::shared_ptr<FaultCounts> counts)
    : inner_{std::move(inner)}, plan_{plan}, counts_{std::move(counts)} {}

std::size_t FaultyDetector::read(std::span<std::uint64_t> out) {
  // TODO: link down, corruption, stall and reordering, following plan_.
  const std::size_t n = inner_->read(out);
  delivered_ += n;
  counts_->delivered.fetch_add(n);
  return n;
}

std::function<std::int64_t(std::uint64_t)> FaultyDetector::due_times() { return inner_->due_times(); }

std::optional<std::string> FaultyDetector::fault() const { return inner_->fault(); }

std::string FaultyDetector::describe() const { return "faulty(" + inner_->describe() + ")"; }

minidaq::control::DetectorFactory faulty_factory(minidaq::control::DetectorFactory inner, FaultPlan plan,
                                                 std::shared_ptr<FaultCounts> counts) {
  return [inner = std::move(inner), plan, counts = std::move(counts)](
             const minidaq::config::AcquisitionConfig& c,
             std::string& error) -> std::unique_ptr<minidaq::control::DetectorPort> {
    auto d = inner(c, error);
    if (!d) {
      return nullptr;
    }
    return std::make_unique<FaultyDetector>(std::move(d), plan, counts);
  };
}

}  // namespace ex
