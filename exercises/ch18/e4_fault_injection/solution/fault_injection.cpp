// SPDX-License-Identifier: MIT
#include "fault_injection.hpp"

#include <algorithm>
#include <utility>

namespace ex {

FaultInjectingDetector::FaultInjectingDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan)
    : inner_{std::move(inner)}, plan_{std::move(plan)} {}

// [snippet:read]
std::size_t FaultInjectingDetector::read(std::span<std::uint64_t> out) {
  const std::uint64_t r = reads_++;
  if (faulted_.load()) {
    return 0;
  }
  if (r >= plan_.stall_from && r - plan_.stall_from < plan_.stall_reads) {
    return 0;
  }
  // Never deliver past the fault: read only as many words as remain before it.
  if (plan_.fault_after_words > 0) {
    const std::uint64_t left = plan_.fault_after_words - delivered_.load();
    out = out.first(static_cast<std::size_t>(std::min<std::uint64_t>(out.size(), left)));
  }
  const std::size_t n = inner_->read(out);
  std::size_t kept = 0;
  for (std::size_t i = 0; i < n; ++i) {
    ++seen_;
    if (plan_.drop_every > 0 && seen_ % plan_.drop_every == 0) {
      dropped_.fetch_add(1);
      continue;
    }
    out[kept++] = out[i];
  }
  const std::uint64_t total = delivered_.fetch_add(kept) + kept;
  if (plan_.fault_after_words > 0 && total >= plan_.fault_after_words) {
    faulted_.store(true);
  }
  return kept;
}
// [/snippet:read]

std::optional<std::string> FaultInjectingDetector::fault() const {
  if (faulted_.load()) {
    return plan_.message;
  }
  return inner_->fault();  // a real fault of the inner port is never hidden
}

std::string FaultInjectingDetector::describe() const { return "fault-injecting(" + inner_->describe() + ")"; }

std::vector<minidaq::control::DetectorCounter> FaultInjectingDetector::counters() const {
  auto c = inner_->counters();
  c.push_back({"rejected_injected", dropped_.load()});
  return c;
}

}  // namespace ex
