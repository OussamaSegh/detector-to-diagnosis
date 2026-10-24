// SPDX-License-Identifier: MIT
// Exercise 9.2: detecting loss, reordering and duplication on a readout link
// from 16-bit sequence numbers, without holding any packets.
#pragma once

#include <bitset>
#include <cstdint>

namespace ex92 {

struct LinkCounts {
  std::uint64_t received = 0;
  std::uint64_t lost = 0;        // sequence numbers that never arrived (so far)
  std::uint64_t reordered = 0;   // arrived after a higher sequence number
  std::uint64_t duplicates = 0;  // arrived more than once
};

// Watches the sequence numbers of one link, the way a firmware or NIC
// counter would: it decides nothing and holds nothing, it counts. The board's
// counter is 16 bits wide and wraps after 65535.
//
// A gap is counted as lost when it appears; a packet that fills it later
// takes it back (lost - 1, reordered + 1). Packets more than `window` behind
// the highest sequence number are too old to tell apart from a duplicate or a
// restart and are counted as duplicates.
class LinkMonitor {
 public:
  static constexpr std::uint16_t window = 1024;
  void on_packet(std::uint16_t seq);
  [[nodiscard]] const LinkCounts& counts() const noexcept { return counts_; }

 private:
  LinkCounts counts_;
  std::uint16_t highest_ = 0;
  bool started_ = false;
  std::bitset<window> seen_;  // seen_[s % window]: s arrived (for s within window of highest_)
};

}  // namespace ex92
