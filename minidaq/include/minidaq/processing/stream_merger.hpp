// SPDX-License-Identifier: MIT
// MiniDAQ - merging the singles streams of many boards into one time-ordered
// stream (Chapter 10).
//
// Each board's stream is in time order, but the boards are not in step: one
// board's packet for a microsecond can arrive after another board's packet for
// the next. The merger holds singles until every board has reported a later
// time (the watermark), then releases them in time order with a k-way merge.
//
//   watermark = min over boards of (latest time the board has reported)
//
// A board reports a time by sending a single or, when it has nothing to send,
// a time marker (advance()). A board that reports nothing at all would hold
// everything back forever, so max_skew bounds the wait: the watermark never
// lags the most advanced board by more than max_skew. A single that arrives
// after its time has been released is late: it is counted and dropped, since
// the sorter has already closed the windows it belonged to.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/core/single.hpp"

namespace minidaq {

// [snippet:config]
struct MergerConfig {
  std::size_t boards = 1;
  // How far the watermark may lag the most advanced board; 0 waits forever.
  Picoseconds max_skew{100'000'000};  // 100 us
};

struct MergerStats {
  std::uint64_t singles_in = 0;
  std::uint64_t singles_out = 0;
  std::uint64_t late = 0;          // arrived after their time was released
  std::uint64_t out_of_order = 0;  // earlier than the same board's previous single
  std::uint64_t skew_releases = 0; // drains where max_skew, not a slow board, set the watermark
  friend bool operator==(const MergerStats&, const MergerStats&) = default;
};
// [/snippet:config]

class StreamMerger {
 public:
  // Throws std::invalid_argument for zero boards.
  explicit StreamMerger(const MergerConfig& cfg);

  // `in` must be in time order for this board, and no earlier than a time
  // marker the board sent; singles that break this are counted and dropped.
  void push(std::size_t board, std::span<const Single> in);
  // The board promises that nothing earlier than `t` follows (a time marker).
  void advance(std::size_t board, Picoseconds t);
  // Appends every held single earlier than the watermark, in time order.
  // Equal times from different boards come out in TimeOrder (then by board);
  // equal times from one board keep that board's order.
  void drain(std::vector<Single>& out);
  // End of run: appends everything held, whatever the watermark.
  void flush(std::vector<Single>& out);

  [[nodiscard]] Picoseconds watermark() const noexcept;
  [[nodiscard]] std::size_t held() const noexcept { return held_; }
  [[nodiscard]] const MergerStats& stats() const noexcept { return stats_; }

 private:
  struct Board {
    std::vector<Single> queue;
    std::size_t head = 0;      // next single to release
    bool reported = false;     // has sent a single or a time marker
    Picoseconds reported_to{}; // latest time reported
    bool in_heap = false;
  };
  void release_until(Picoseconds limit, std::vector<Single>& out);
  [[nodiscard]] bool later(std::size_t a, std::size_t b) const noexcept;  // heap order

  MergerConfig cfg_;
  std::vector<Board> boards_;
  std::vector<std::size_t> heap_;  // boards with held singles, earliest head on top
  bool released_any_ = false;
  Picoseconds released_to_{};      // every single earlier than this has been released
  std::size_t held_ = 0;
  MergerStats stats_{};
};

}  // namespace minidaq
