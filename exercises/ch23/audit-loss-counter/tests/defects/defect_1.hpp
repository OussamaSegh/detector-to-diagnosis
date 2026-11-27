// SPDX-License-Identifier: MIT
// Exercise 23.5 (A): the loss counter of one readout link. The receiver offers
// the 32-bit sequence number of every packet that arrives; the counter says how
// many packets the network lost, which is how the operator judges whether a
// scan is complete. Sequence numbers wrap from 2^32 - 1 to 0.
#pragma once

#include <cstdint>

namespace ex235 {

struct LossStats {
  std::uint64_t received = 0;   // packets offered
  std::uint64_t lost = 0;       // sequence numbers missing now
  std::uint64_t reordered = 0;  // arrived after a higher sequence number, and filled its gap
  std::uint64_t stale = 0;      // copies of a packet already received
  std::uint64_t resyncs = 0;    // the link restarted its numbering
};

// The signed distance from `from` to `to` (RFC 1982's idea): right across the
// wrap while the two are less than 2^31 apart.
constexpr std::int32_t sequence_distance(std::uint32_t from, std::uint32_t to) noexcept {
  return static_cast<std::int32_t>(to - from);
}

class LossCounter {
 public:
  static constexpr std::uint32_t window = 64;  // how far back a late packet is still placed

  explicit LossCounter(std::uint32_t max_gap = std::uint32_t{1} << 24) noexcept
      : max_gap_{max_gap} {}

  void offer(std::uint32_t seq) noexcept {
    ++stats_.received;
    if (!started_) {
      restart(seq);
      return;
    }
    const std::int32_t behind = sequence_distance(seq, next_);
    if (behind > 0) {  // a late packet
      if (static_cast<std::uint32_t>(behind) > window) {
        ++stats_.resyncs;  // too far back to be late: the link restarted
        restart(seq);
        return;
      }
      const std::uint64_t bit = std::uint64_t{1} << (behind - 1);
      if ((seen_ & bit) != 0) {
        ++stats_.stale;  // a copy of one we have
        return;
      }
      ++stats_.reordered;  // it arrived after a higher sequence number
      seen_ |= bit;
      --stats_.lost;  // it fills its gap
      return;
    }
    const std::int32_t ahead = sequence_distance(next_, seq);
    if (ahead > static_cast<std::int32_t>(max_gap_)) {
      ++stats_.resyncs;  // a jump no network makes: the link restarted
      restart(seq);
      return;
    }
    stats_.lost += static_cast<std::uint32_t>(ahead);  // the numbers skipped
    advance(static_cast<std::uint64_t>(static_cast<std::uint32_t>(ahead)) + 1);
  }

  [[nodiscard]] const LossStats& stats() const noexcept { return stats_; }

 private:
  // Bit k of seen_ is set if sequence number next_ - 1 - k was received.
  void advance(std::uint64_t n) noexcept {
    seen_ = n >= 64 ? 0 : seen_ << n;
    seen_ |= 1;
    next_ += static_cast<std::uint32_t>(n);
  }
  void restart(std::uint32_t seq) noexcept {
    started_ = true;
    next_ = seq + 1;
    seen_ = ~std::uint64_t{0};  // nothing before the first packet is missing
  }

  std::uint32_t max_gap_;
  bool started_ = false;
  std::uint32_t next_ = 0;
  std::uint64_t seen_ = 0;
  LossStats stats_;
};

}  // namespace ex235
