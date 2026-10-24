// SPDX-License-Identifier: MIT
// MiniDAQ - replaying recorded MDQ-P1 words at a fixed rate (Chapter 11).
//
// PacedSource (Chapter 4) delivers synthetic words, whose energies and
// crystals are uniform; a throughput measurement with them says little about
// the sorter, whose work depends on how many singles pass the energy window
// and how often windows hold several singles. ReplaySource delivers a recorded
// stream instead (for example the simulator's output, `minidaq_sim --words`)
// on the same wall-clock schedule as PacedSource. When the recording runs out
// it starts again, with every time stamp shifted by the recording's length,
// so the stream stays in time order for as long as the run lasts.
#pragma once

#include <algorithm>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/format/packed_single.hpp"

namespace minidaq::sim {

class ReplaySource {
 public:
  // `words` must be in time order. words_per_second <= 0 replays in real time:
  // at the rate the recording's own time stamps imply.
  ReplaySource(std::vector<std::uint64_t> words, double words_per_second, std::size_t max_burst = 4096)
      : words_{std::move(words)}, max_burst_{max_burst} {
    if (words_.size() < 2) {
      throw std::invalid_argument("ReplaySource: need at least two words");
    }
    packed::TimeUnwrapper unwrap;
    const Picoseconds first = unwrap.unwrap(packed::unpack(words_.front()).time_code);
    Picoseconds last = first;
    for (const std::uint64_t w : words_) {
      last = unwrap.unwrap(packed::unpack(w).time_code);
    }
    const std::int64_t span_ps = (last - first).count();
    // One loop lasts the recording plus one mean gap, so the first word of the
    // next loop does not coincide with the last word of this one.
    const std::int64_t gap_ps = span_ps / static_cast<std::int64_t>(words_.size() - 1);
    period_codes_ = static_cast<std::uint64_t>((span_ps + gap_ps) / packed::time_lsb_ps);
    if (period_codes_ == 0 || 2 * period_codes_ > packed::time_mask) {
      throw std::invalid_argument("ReplaySource: the recording must last between 5 ps and half a wrap period");
    }
    real_time_rate_ = static_cast<double>(words_.size()) * 1e12 / static_cast<double>(span_ps + gap_ps);
    rate_per_ns_ = (words_per_second > 0.0 ? words_per_second : real_time_rate_) * 1e-9;
  }

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
    for (std::size_t i = 0; i < n; ++i) {
      const std::uint64_t index = delivered_ + i;
      const std::uint64_t loop = index / words_.size();
      const std::uint64_t w = words_[index % words_.size()];
      // Shift the 38-bit time field by whole loops; it wraps like the hardware
      // counter, and the decoder unwraps it.
      const std::uint64_t t = (w + loop * period_codes_) & packed::time_mask;
      out[i] = (w & ~packed::time_mask) | t;
    }
    delivered_ += n;
    return n;
  }

  // Changes the delivery rate; only before the first call.
  void set_rate(double words_per_second) {
    if (start_ns_ != 0 || !(words_per_second > 0.0)) {
      throw std::logic_error("ReplaySource::set_rate: a positive rate, before the first call");
    }
    rate_per_ns_ = words_per_second * 1e-9;
  }

  [[nodiscard]] std::uint64_t delivered() const noexcept { return delivered_; }
  [[nodiscard]] double real_time_rate() const noexcept { return real_time_rate_; }
  [[nodiscard]] double rate() const noexcept { return rate_per_ns_ * 1e9; }
  [[nodiscard]] std::uint64_t behind(std::int64_t now_ns) const noexcept {
    if (start_ns_ == 0) {
      return 0;
    }
    const auto due = static_cast<std::uint64_t>(static_cast<double>(now_ns - start_ns_) * rate_per_ns_);
    return due > delivered_ ? due - delivered_ : 0;
  }
  [[nodiscard]] std::int64_t due_ns(std::uint64_t index) const noexcept {
    return start_ns_ + static_cast<std::int64_t>(static_cast<double>(index) / rate_per_ns_);
  }

 private:
  std::vector<std::uint64_t> words_;
  std::size_t max_burst_;
  std::uint64_t period_codes_ = 0;
  double real_time_rate_ = 0.0;
  double rate_per_ns_ = 0.0;
  std::int64_t start_ns_ = 0;
  std::uint64_t delivered_ = 0;
};

}  // namespace minidaq::sim
