// SPDX-License-Identifier: MIT
#include "minidaq/processing/node_merge.hpp"

#include <limits>
#include <stdexcept>
#include <utility>

namespace minidaq {

NodeMerge::NodeMerge(std::vector<Picoseconds> clock_offsets)
    // The StreamMerger refuses zero boards with std::invalid_argument, so no nodes is refused too.
    : offsets_{std::move(clock_offsets)},
      merger_{{.boards = offsets_.size(), .max_skew = Picoseconds{0}}} {}

// [snippet:push]
void NodeMerge::push(std::size_t node, std::span<const Single> in) {
  const Picoseconds offset = offsets_.at(node);
  corrected_.assign(in.begin(), in.end());
  for (Single& s : corrected_) {
    s.time -= offset;  // the node's clock to true time; a constant keeps the order
  }
  merger_.push(node, corrected_);
}
// [/snippet:push]

void NodeMerge::advance(std::size_t node, Picoseconds node_time) {
  merger_.advance(node, node_time - offsets_.at(node));
}

void NodeMerge::end(std::size_t node) {
  if (node >= offsets_.size()) {
    throw std::out_of_range("NodeMerge::end: no such node");
  }
  merger_.advance(node, Picoseconds{std::numeric_limits<std::int64_t>::max()});
}

void NodeMerge::drain(std::vector<Single>& out) { merger_.drain(out); }

void NodeMerge::flush(std::vector<Single>& out) { merger_.flush(out); }

}  // namespace minidaq
