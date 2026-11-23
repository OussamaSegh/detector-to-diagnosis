// SPDX-License-Identifier: MIT
// MiniDAQ - the scanner's blocks read out by several nodes (CR-0037, roadmap 2.2.0).
//
// A larger scanner reads its detector blocks out through several acquisition
// PCs. Each one, a readout node, sends a time-ordered stream of the singles of
// its own blocks, stamped with its own clock: a node's clock reads the true
// time plus that node's offset. The simulator plays such nodes in one process,
// so that the node merge (minidaq/processing/node_merge.hpp) can be specified,
// tested against one stream and measured before nodes are separate machines.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"
#include "minidaq/sim/synthetic_source.hpp"

namespace minidaq::sim {

inline constexpr std::size_t max_readout_nodes = 8;
// The largest clock offset of a node, either way.
inline constexpr Picoseconds max_node_clock_offset{1'000'000};  // 1 us

// Which node reads each block, and each node's clock offset.
struct NodeLayout {
  std::vector<std::uint32_t> node_of_block;  // one entry per block of the scanner
  std::vector<Picoseconds> clock_offset;     // one entry per node

  // `nodes` contiguous ranges of blocks, as even as they divide. An empty
  // `offsets` gives every node offset 0. Throws std::invalid_argument when
  // the layout is not valid().
  [[nodiscard]] static NodeLayout contiguous(std::size_t nodes,
                                             std::vector<Picoseconds> offsets = {});
  // One node per block, as listed. Throws std::invalid_argument when the
  // layout is not valid().
  [[nodiscard]] static NodeLayout of_blocks(std::vector<std::uint32_t> node_of_block,
                                            std::vector<Picoseconds> offsets);

  // 1 to 8 nodes, one offset per node of at most 1 us either way, every block
  // read by one of them. Returns what is wrong, or an empty string.
  [[nodiscard]] std::string invalid() const;
  [[nodiscard]] std::size_t nodes() const noexcept { return clock_offset.size(); }
  [[nodiscard]] std::size_t node_of(CrystalId c) const noexcept {
    return node_of_block[ScannerGeometry::block_of(c)];
  }
};

// Divides a time-ordered stream of singles among the nodes. Each node's part
// stays in time order, since a constant offset does not reorder a stream.
class NodeSplitter {
 public:
  explicit NodeSplitter(NodeLayout layout);

  // Appends each single of `in`, stamped with its node's clock, to out[node].
  // `out` is resized to nodes() when it has another size.
  void split(std::span<const Single> in, std::vector<std::vector<Single>>& out) const;
  // What node `node`'s clock reads at true time `t`.
  [[nodiscard]] Picoseconds node_time(std::size_t node, Picoseconds t) const noexcept {
    return t + layout_.clock_offset[node];
  }
  [[nodiscard]] const NodeLayout& layout() const noexcept { return layout_; }

 private:
  NodeLayout layout_;
};

}  // namespace minidaq::sim
