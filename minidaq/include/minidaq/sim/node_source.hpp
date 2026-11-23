// SPDX-License-Identifier: MIT
// MiniDAQ - a synthetic source read out by several nodes and merged (CR-0037).
//
// The source stage's input when a configuration names several readout nodes:
// the synthetic singles are divided among the nodes (NodeSplitter), each node
// stamps them with its own clock and reports its time after each step, and the
// node merge (minidaq/processing/node_merge.hpp) corrects the clocks and merges
// the streams back into one, which is packed into MDQ-P1 words as the
// synthetic source packs its own. The nodes are played in one process: what
// a network between them would do is roadmap 3.0.0, Chapters 41 and 42.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/processing/node_merge.hpp"
#include "minidaq/sim/readout_nodes.hpp"
#include "minidaq/sim/synthetic_source.hpp"

namespace minidaq::sim {

class MultiNodeSource {
 public:
  // Throws std::invalid_argument when the layout is not valid.
  MultiNodeSource(SyntheticConfig cfg, NodeLayout layout);

  // Fills `out` with packed words of the merged stream; returns out.size().
  std::size_t generate(std::span<std::uint64_t> out);
  // The same, unpacked, in true time.
  void generate(std::span<Single> out);

  [[nodiscard]] const NodeMerge& merge() const noexcept { return merge_; }

 private:
  void refill(std::size_t wanted);

  SyntheticSource gen_;
  NodeSplitter splitter_;
  NodeMerge merge_;
  std::vector<Single> fresh_;                  // one step's singles, in true time
  std::vector<std::vector<Single>> per_node_;  // the same, divided, in each node's clock
  std::vector<Single> merged_;                 // released by the merge, not yet delivered
  std::size_t next_ = 0;                       // first of merged_ not yet delivered
};

}  // namespace minidaq::sim
