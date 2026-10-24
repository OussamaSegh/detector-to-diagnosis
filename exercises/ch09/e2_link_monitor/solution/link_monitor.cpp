// SPDX-License-Identifier: MIT
#include "link_monitor.hpp"

namespace ex92 {

// [snippet:monitor]
void LinkMonitor::on_packet(std::uint16_t seq) {
  ++counts_.received;
  if (!started_) {
    started_ = true;
    highest_ = seq;
    seen_.set(seq % std::size_t{window});
    return;
  }
  // Signed distance modulo 2^16: correct across the wrap from 65535 to 0.
  const auto ahead = static_cast<std::int16_t>(static_cast<std::uint16_t>(seq - highest_));
  if (ahead > 0) {
    // New highest. Everything skipped is missing for now; forget the slots
    // that slide out of the window.
    if (ahead >= window) {
      seen_.reset();  // a huge gap: nothing in the window is known any more
    } else {
      for (std::uint16_t s = static_cast<std::uint16_t>(highest_ + 1); s != seq; ++s) {
        seen_.reset(s % std::size_t{window});
      }
    }
    counts_.lost += static_cast<std::uint64_t>(ahead - 1);
    highest_ = seq;
    seen_.set(seq % std::size_t{window});
  } else if (ahead == 0 || -ahead >= window) {
    ++counts_.duplicates;  // the latest one again, or too old to tell
  } else if (seen_.test(seq % std::size_t{window})) {
    ++counts_.duplicates;
  } else {
    seen_.set(seq % std::size_t{window});  // a gap is filled: it was late, not lost
    --counts_.lost;
    ++counts_.reordered;
  }
}
// [/snippet:monitor]

}  // namespace ex92
