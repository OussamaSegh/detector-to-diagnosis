// SPDX-License-Identifier: MIT
// Exercise 21.3: a flight recorder for one thread. One writer records events into a ring of
// kEvents slots; any other thread may take a snapshot at any time, and the snapshot holds only
// complete events, never half of one (a seqlock per slot, as in minidaq/core/flight_recorder).
#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <span>

namespace ex21 {

struct Event {
  std::uint64_t seq = 0;  // the event's number, from 1
  std::uint64_t a = 0;
  std::uint64_t b = 0;
};

class TinyRecorder {
 public:
  static constexpr std::size_t kEvents = 64;  // a power of two

  // Only one thread calls record(). Wait-free.
  void record(std::uint64_t a, std::uint64_t b) noexcept;
  // Any thread. The newest complete events, oldest first, at most out.size(); returns how many.
  std::size_t snapshot(std::span<Event> out) const noexcept;
  // Events a snapshot skipped because the writer overwrote them while it copied, so far.
  [[nodiscard]] std::uint64_t torn() const noexcept { return torn_.load(std::memory_order_relaxed); }

 private:
  struct Slot {
    // TODO: what does a reader need to tell a complete event from one being written?
    std::atomic<std::uint64_t> a{0};
    std::atomic<std::uint64_t> b{0};
  };
  std::array<Slot, kEvents> slots_{};
  std::atomic<std::uint64_t> next_{0};  // events recorded so far
  mutable std::atomic<std::uint64_t> torn_{0};
};

}  // namespace ex21
