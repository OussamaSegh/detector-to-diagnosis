// SPDX-License-Identifier: MIT
#include "minidaq/processing/stream_merger.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

#include "minidaq/pipeline/acquisition_pipeline.hpp"

namespace minidaq {

namespace {
std::size_t checked_boards(const MergerConfig& c) {
  if (c.boards == 0 || c.max_skew < Picoseconds{0}) {
    throw std::invalid_argument("MergerConfig: at least one board and max_skew >= 0");
  }
  return c.boards;
}
}  // namespace

StreamMerger::StreamMerger(const MergerConfig& cfg) : cfg_{cfg}, boards_(checked_boards(cfg)) {
  heap_.reserve(boards_.size());
}

// [snippet:push]
void StreamMerger::push(std::size_t board, std::span<const Single> in) {
  Board& b = boards_.at(board);
  for (const Single& s : in) {
    ++stats_.singles_in;
    if (b.reported && s.time < b.reported_to) {
      ++stats_.out_of_order;
      continue;
    }
    b.reported = true;
    b.reported_to = s.time;
    if (released_any_ && s.time < released_to_) {
      ++stats_.late;  // its windows are closed: it can no longer be placed
      continue;
    }
    if (b.head > 4096 && b.head * 2 > b.queue.size()) {
      b.queue.erase(b.queue.begin(), b.queue.begin() + static_cast<std::ptrdiff_t>(b.head));
      b.head = 0;  // same head single, so the heap order is unchanged
    }
    b.queue.push_back(s);
    ++held_;
  }
  if (!b.in_heap && b.head < b.queue.size()) {
    heap_.push_back(board);
    std::push_heap(heap_.begin(), heap_.end(), [this](std::size_t x, std::size_t y) { return later(x, y); });
    b.in_heap = true;
  }
}
// [/snippet:push]

void StreamMerger::advance(std::size_t board, Picoseconds t) {
  Board& b = boards_.at(board);
  if (!b.reported || t > b.reported_to) {
    b.reported = true;
    b.reported_to = t;
  }
}

// [snippet:watermark]
Picoseconds StreamMerger::watermark() const noexcept {
  Picoseconds lo{std::numeric_limits<std::int64_t>::max()};
  Picoseconds hi{std::numeric_limits<std::int64_t>::min()};
  for (const Board& b : boards_) {
    if (!b.reported) {
      return Picoseconds{std::numeric_limits<std::int64_t>::min()};  // nothing known about this board yet
    }
    lo = std::min(lo, b.reported_to);
    hi = std::max(hi, b.reported_to);
  }
  if (cfg_.max_skew > Picoseconds{0} && hi - lo > cfg_.max_skew) {
    return hi - cfg_.max_skew;  // a slow or silent board no longer holds everyone back
  }
  return lo;
}
// [/snippet:watermark]

void StreamMerger::drain(std::vector<Single>& out) {
  // Until every board has reported at least once there is no watermark: a
  // board that has never been heard from could still send anything.
  const Picoseconds w = watermark();
  if (w == Picoseconds{std::numeric_limits<std::int64_t>::min()}) {
    return;
  }
  Picoseconds lo{std::numeric_limits<std::int64_t>::max()};
  for (const Board& b : boards_) {
    lo = std::min(lo, b.reported_to);
  }
  if (w > lo) {
    ++stats_.skew_releases;
  }
  release_until(w, out);
  if (!released_any_ || w > released_to_) {
    released_any_ = true;
    released_to_ = w;
  }
}

void StreamMerger::flush(std::vector<Single>& out) {
  release_until(Picoseconds{std::numeric_limits<std::int64_t>::max()}, out);
  for (Board& b : boards_) {
    b = Board{};
  }
  heap_.clear();
  released_any_ = false;
  held_ = 0;
}

bool StreamMerger::later(std::size_t a, std::size_t b) const noexcept {
  const Single& x = boards_[a].queue[boards_[a].head];
  const Single& y = boards_[b].queue[boards_[b].head];
  if (time_order(y, x)) {
    return true;
  }
  if (time_order(x, y)) {
    return false;
  }
  return a > b;  // a complete tie: the lower board first, so the output is deterministic
}

// [snippet:release]
void StreamMerger::release_until(Picoseconds limit, std::vector<Single>& out) {
  const auto cmp = [this](std::size_t x, std::size_t y) { return later(x, y); };
  while (!heap_.empty()) {
    const std::size_t i = heap_.front();
    Board& b = boards_[i];
    const Single& s = b.queue[b.head];
    if (!(s.time < limit)) {
      break;  // the earliest held single is not yet safe to release
    }
    std::pop_heap(heap_.begin(), heap_.end(), cmp);
    out.push_back(s);
    ++b.head;
    --held_;
    ++stats_.singles_out;
    if (b.head < b.queue.size()) {
      std::push_heap(heap_.begin(), heap_.end(), cmp);  // the board's next single takes its place
    } else {
      heap_.pop_back();
      b.in_heap = false;
      b.queue.clear();
      b.head = 0;
    }
  }
}
// [/snippet:release]

}  // namespace minidaq
