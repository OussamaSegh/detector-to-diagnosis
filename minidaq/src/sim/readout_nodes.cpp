// SPDX-License-Identifier: MIT
#include "minidaq/sim/readout_nodes.hpp"

#include <stdexcept>
#include <string>

namespace minidaq::sim {

namespace {
NodeLayout checked(NodeLayout l) {
  if (const std::string e = l.invalid(); !e.empty()) {
    throw std::invalid_argument("NodeLayout: " + e);
  }
  return l;
}
}  // namespace

NodeLayout NodeLayout::contiguous(std::size_t nodes, std::vector<Picoseconds> offsets) {
  if (offsets.empty()) {
    offsets.assign(nodes, Picoseconds{0});
  }
  NodeLayout l;
  l.clock_offset = std::move(offsets);
  constexpr std::size_t blocks = ScannerGeometry::num_blocks;
  l.node_of_block.resize(blocks);
  for (std::size_t b = 0; b < blocks; ++b) {
    // nodes == 0 is caught by invalid(); avoid dividing by it before then.
    l.node_of_block[b] = nodes == 0 ? 0 : static_cast<std::uint32_t>(b * nodes / blocks);
  }
  return checked(std::move(l));
}

NodeLayout NodeLayout::of_blocks(std::vector<std::uint32_t> node_of_block,
                                 std::vector<Picoseconds> offsets) {
  return checked(NodeLayout{std::move(node_of_block), std::move(offsets)});
}

std::string NodeLayout::invalid() const {
  if (nodes() < 1 || nodes() > max_readout_nodes) {
    return "from 1 to " + std::to_string(max_readout_nodes) + " nodes, one clock offset each";
  }
  for (const Picoseconds o : clock_offset) {
    if (o > max_node_clock_offset || o < -max_node_clock_offset) {
      return "a clock offset of at most 1 us either way";
    }
  }
  if (node_of_block.size() != ScannerGeometry::num_blocks) {
    return "one node for each of the " + std::to_string(ScannerGeometry::num_blocks) + " blocks";
  }
  for (const std::uint32_t n : node_of_block) {
    if (n >= nodes()) {
      return "a block read by node " + std::to_string(n) + " of " + std::to_string(nodes());
    }
  }
  return {};
}

NodeSplitter::NodeSplitter(NodeLayout layout) : layout_{checked(std::move(layout))} {}

void NodeSplitter::split(std::span<const Single> in, std::vector<std::vector<Single>>& out) const {
  out.resize(layout_.nodes());
  for (const Single& s : in) {
    const std::size_t n = layout_.node_of(s.crystal);
    Single stamped = s;
    stamped.time = node_time(n, s.time);
    out[n].push_back(stamped);
  }
}

}  // namespace minidaq::sim
