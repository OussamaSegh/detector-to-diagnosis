// SPDX-License-Identifier: MIT
// Exercise 6.5 solution.
#include "faulty_detector.hpp"

#include <algorithm>

#include "minidaq/format/packed_single.hpp"

namespace ex {

FaultyDetector::FaultyDetector(std::unique_ptr<minidaq::control::DetectorPort> inner, FaultPlan plan,
                               std::shared_ptr<FaultCounts> counts)
    : inner_{std::move(inner)}, plan_{plan}, counts_{std::move(counts)} {}

// [snippet:read]
std::size_t FaultyDetector::read(std::span<std::uint64_t> out) {
  using clock = std::chrono::steady_clock;
  if (link_down_.load(std::memory_order_relaxed)) {
    return 0;  // a dead link delivers nothing
  }
  if (plan_.stall_after_words != 0 && !stalled_ && delivered_ >= plan_.stall_after_words) {
    stalled_ = true;
    stall_end_ = clock::now() + plan_.stall_for;
    counts_->stalls.fetch_add(1);
  }
  if (stalled_ && clock::now() < stall_end_) {
    return 0;  // stalled: the inner source keeps its schedule, so a backlog builds
  }
  // Release held-back words once enough newer words have gone out.
  if (!held_.empty() && delivered_ >= release_at_) {
    const std::size_t n = std::min(out.size(), held_.size());
    std::copy_n(held_.begin(), n, out.begin());
    held_.erase(held_.begin(), held_.begin() + static_cast<std::ptrdiff_t>(n));
    delivered_ += n;
    counts_->delivered.fetch_add(n);
    return n;
  }
  std::size_t n = inner_->read(out);
  if (n == 0) {
    return 0;
  }
  if (plan_.reorder_after_words != 0 && !reordered_ && delivered_ >= plan_.reorder_after_words) {
    reordered_ = true;  // hold this read back
    held_.assign(out.begin(), out.begin() + static_cast<std::ptrdiff_t>(n));
    counts_->reordered.fetch_add(n);
    release_at_ = delivered_ + plan_.reorder_delay_words;
    return 0;
  }
  if (plan_.corrupt_every != 0) {
    for (std::size_t i = 0; i < n; ++i) {
      if ((delivered_ + i + 1) % plan_.corrupt_every == 0) {
        out[i] |= minidaq::packed::crystal_mask << minidaq::packed::crystal_shift;  // id 32767: no such crystal
        counts_->corrupted.fetch_add(1);
      }
    }
  }
  delivered_ += n;
  counts_->delivered.fetch_add(n);
  if (plan_.link_down_after_words != 0 && delivered_ >= plan_.link_down_after_words) {
    link_down_.store(true, std::memory_order_relaxed);
  }
  return n;
}
// [/snippet:read]

std::function<std::int64_t(std::uint64_t)> FaultyDetector::due_times() {
  // Word i of the output was word i of the inner source, except while words are
  // held back; for a test of latency under a stall that approximation is fine.
  return inner_->due_times();
}

std::optional<std::string> FaultyDetector::fault() const {
  if (link_down_.load(std::memory_order_relaxed)) {
    return "link down after " + std::to_string(plan_.link_down_after_words) + " words";
  }
  return inner_->fault();
}

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
