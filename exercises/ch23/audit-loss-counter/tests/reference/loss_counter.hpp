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
    // Modular distance ahead: below 2^31 the packet is ahead of next_ (0 is in
    // order), from 2^31 on it is behind by 2^32 minus that. Exactly 2^31 is
    // neither (serial arithmetic is undefined there): too far either way.
    const std::uint32_t ahead = seq - next_;
    if (ahead >= (std::uint32_t{1} << 31)) {  // a late packet
      const std::uint32_t behind = next_ - seq;
      if (behind > window) {
        ++stats_.resyncs;  // too far back to be late: the link restarted
        restart(seq);
        return;
      }
      const std::uint64_t bit = std::uint64_t{1} << (behind - 1);
      if ((seen_ & bit) != 0) {
        ++stats_.stale;  // a copy of one we have: not reordered, not used
        return;
      }
      ++stats_.reordered;  // it arrived after a higher sequence number, and is used
      seen_ |= bit;
      --stats_.lost;  // it fills its gap
      return;
    }
    if (ahead > max_gap_) {
      ++stats_.resyncs;  // a jump no network makes: the link restarted
      restart(seq);
      return;
    }
    stats_.lost += ahead;  // the numbers skipped
    advance(std::uint64_t{ahead} + 1);
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
