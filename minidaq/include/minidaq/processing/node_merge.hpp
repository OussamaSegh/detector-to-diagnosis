// SPDX-License-Identifier: MIT
// MiniDAQ - merging the streams of several readout nodes (CR-0037, roadmap 2.2.0).
//
// Each node sends a time-ordered stream in its own clock, which reads the true
// time plus the node's configured offset. The merge subtracts each node's
// offset and merges the streams with the StreamMerger of Chapter 10, waiting
// for every node: a single is released only when every node has delivered a
// later time (a single or a time marker) or has ended. That hold is the overlap
// at the nodes' boundaries, stated in time: a coincidence whose two singles
// come from two nodes is formed as it would be from one stream.
//
// A single that arrives after its time was released is late: it is counted,
// never dropped silently (SRS-MRG-003). Unlike the boards of Chapter 10 the
// merge has no max_skew: a node that stops sending holds the run back until it
// ends, since releasing past it could lose its coincidences.
#pragma once

#include <cstddef>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/processing/stream_merger.hpp"

namespace minidaq {

class NodeMerge {
 public:
  // One clock offset per node. Throws std::invalid_argument for no nodes.
  explicit NodeMerge(std::vector<Picoseconds> clock_offsets);

  // A node's singles in its own clock, in time order.
  void push(std::size_t node, std::span<const Single> in);
  // A node's time marker in its own clock: nothing earlier follows from it.
  void advance(std::size_t node, Picoseconds node_time);
  // The node has ended: it holds nothing back any more.
  void end(std::size_t node);
  // Appends, in time order and in true time, every single that every node is past.
  void drain(std::vector<Single>& out);
  // End of run: appends everything held.
  void flush(std::vector<Single>& out);

  [[nodiscard]] std::size_t nodes() const noexcept { return offsets_.size(); }
  [[nodiscard]] std::size_t held() const noexcept { return merger_.held(); }
  [[nodiscard]] const MergerStats& stats() const noexcept { return merger_.stats(); }

 private:
  std::vector<Picoseconds> offsets_;
  StreamMerger merger_;
  std::vector<Single> corrected_;  // scratch: one push's singles in true time
};

}  // namespace minidaq
