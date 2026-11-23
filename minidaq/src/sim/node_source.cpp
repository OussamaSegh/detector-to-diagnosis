// SPDX-License-Identifier: MIT
#include "minidaq/sim/node_source.hpp"

#include <algorithm>

#include "minidaq/format/packed_single.hpp"

namespace minidaq::sim {

MultiNodeSource::MultiNodeSource(SyntheticConfig cfg, NodeLayout layout)
    : gen_{cfg}, splitter_{std::move(layout)}, merge_{splitter_.layout().clock_offset} {}

// [snippet:refill]
void MultiNodeSource::refill(std::size_t wanted) {
  if (next_ > 0) {
    merged_.erase(merged_.begin(), merged_.begin() + static_cast<std::ptrdiff_t>(next_));
    next_ = 0;
  }
  while (merged_.size() < wanted) {
    // One step of the scanner: new singles, divided among the nodes in their clocks.
    fresh_.resize(std::max<std::size_t>(wanted - merged_.size(), 256));
    gen_.generate(std::span<Single>{fresh_});
    for (auto& v : per_node_) {
      v.clear();
    }
    splitter_.split(fresh_, per_node_);
    // Each node sends its singles, then its time marker: the generator's time
    // only grows, so no node will send anything earlier than the last single.
    const Picoseconds now = fresh_.back().time;
    for (std::size_t n = 0; n < per_node_.size(); ++n) {
      merge_.push(n, per_node_[n]);
      merge_.advance(n, splitter_.node_time(n, now));
    }
    merge_.drain(merged_);
  }
}
// [/snippet:refill]

void MultiNodeSource::generate(std::span<Single> out) {
  refill(out.size());
  std::copy_n(merged_.begin() + static_cast<std::ptrdiff_t>(next_), out.size(), out.begin());
  next_ += out.size();
}

std::size_t MultiNodeSource::generate(std::span<std::uint64_t> out) {
  refill(out.size());
  for (auto& w : out) {
    w = packed::encode(merged_[next_++]);
  }
  return out.size();
}

}  // namespace minidaq::sim
