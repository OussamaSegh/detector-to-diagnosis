// SPDX-License-Identifier: MIT
// MiniDAQ - a synthetic source that delivers words at a fixed rate (Chapter 4).
//
// Latency is only meaningful at a given load: a source that produces as fast
// as it can fills every queue and measures queueing, not processing. This
// wrapper releases words according to the wall clock: after t seconds, about
// rate * t words have been delivered in total, in chunks of at most
// max_burst. If the consumer falls behind, the backlog is delivered as fast as
// it is accepted (the hardware does not wait), which is what exposes stalls.
#pragma once

#include <algorithm>
#include <cstdint>
#include <span>

#include "minidaq/core/clock.hpp"
#include "minidaq/sim/synthetic_source.hpp"

namespace minidaq::sim {

class PacedSource {
 public:
  PacedSource(SyntheticConfig cfg, double words_per_second, std::size_t max_burst = 4096)
      : gen_{cfg}, rate_per_ns_{words_per_second * 1e-9}, max_burst_{max_burst} {}

  // Fills up to out.size() words that are due by now; returns how many.
  std::size_t operator()(std::span<std::uint64_t> out) {
    const std::int64_t now = monotonic_ns();
    if (start_ns_ == 0) {
      start_ns_ = now;
    }
    const auto due = static_cast<std::uint64_t>(static_cast<double>(now - start_ns_) * rate_per_ns_);
    if (due <= delivered_) {
      return 0;
    }
    const auto n = static_cast<std::size_t>(std::min<std::uint64_t>({due - delivered_, out.size(), max_burst_}));
    gen_.generate(out.first(n));
    delivered_ += n;
    return n;
  }
  [[nodiscard]] std::uint64_t delivered() const noexcept { return delivered_; }
  // Words due by now_ns that have not been delivered: the backlog a real
  // receiver would hold in its buffers (or lose when they overflow).
  [[nodiscard]] std::uint64_t behind(std::int64_t now_ns) const noexcept {
    if (start_ns_ == 0) {
      return 0;
    }
    const auto due = static_cast<std::uint64_t>(static_cast<double>(now_ns - start_ns_) * rate_per_ns_);
    return due > delivered_ ? due - delivered_ : 0;
  }
  // When word number `index` was due, in monotonic ns (valid after the first call).
  [[nodiscard]] std::int64_t due_ns(std::uint64_t index) const noexcept {
    return start_ns_ + static_cast<std::int64_t>(static_cast<double>(index) / rate_per_ns_);
  }

 private:
  SyntheticSource gen_;
  double rate_per_ns_;
  std::size_t max_burst_;
  std::int64_t start_ns_ = 0;
  std::uint64_t delivered_ = 0;
};

}  // namespace minidaq::sim
