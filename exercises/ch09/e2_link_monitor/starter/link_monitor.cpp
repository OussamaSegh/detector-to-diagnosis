// SPDX-License-Identifier: MIT
#include "link_monitor.hpp"

namespace ex92 {

// TODO(9.2): this monitor is right on a clean link and badly wrong on a real
// one. Reordering, duplicates and the wrap of the 16-bit counter all break
// it. Find each failure with the tests, then fix it.
void LinkMonitor::on_packet(std::uint16_t seq) {
  ++counts_.received;
  if (!started_) {
    started_ = true;
    highest_ = seq;
    return;
  }
  const std::uint16_t gap = static_cast<std::uint16_t>(seq - highest_);
  if (gap > 1) {
    counts_.lost += gap - 1U;
  }
  highest_ = seq;
}

}  // namespace ex92
