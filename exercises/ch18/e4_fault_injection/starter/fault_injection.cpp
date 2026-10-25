// SPDX-License-Identifier: MIT
// Exercise 18.4: the starter passes every word through and injects nothing.
#include "fault_injection.hpp"

#include <utility>

namespace ex {

FaultInjectingDetector::FaultInjectingDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan)
    : inner_{std::move(inner)}, plan_{std::move(plan)} {}

std::size_t FaultInjectingDetector::read(std::span<std::uint64_t> out) {
  // TODO: stalls, drops (counted), and the fault after plan_.fault_after_words,
  // without ever delivering a word past it or reading the inner port after it.
  const std::size_t n = inner_->read(out);
  delivered_.fetch_add(n);
  return n;
}

std::optional<std::string> FaultInjectingDetector::fault() const {
  return inner_->fault();  // TODO: the injected fault
}

std::string FaultInjectingDetector::describe() const { return inner_->describe(); }  // TODO

std::vector<minidaq::control::DetectorCounter> FaultInjectingDetector::counters() const {
  return inner_->counters();  // TODO: and the dropped words
}

}  // namespace ex
