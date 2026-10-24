// SPDX-License-Identifier: MIT
// MiniDAQ - bounded multi-producer multi-consumer queue (Chapter 3).
//
// Dmitry Vyukov's bounded MPMC algorithm: every slot carries a sequence
// number that tells producers and consumers whether the slot is ready for
// them. Producers claim a position with a CAS on enqueue_pos_, consumers with
// a CAS on dequeue_pos_. It is lock-free in practice but not wait-free: a
// producer preempted between claiming a slot and publishing it blocks the
// consumer of that slot. MiniDAQ uses it where several boards' receiver
// threads feed one merger (Chapter 9); SPSC rings everywhere else.
#pragma once

#include <atomic>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <type_traits>
#include <utility>

#include "minidaq/core/cache.hpp"

namespace minidaq {

template <typename T>
class MpmcQueue {
  static_assert(std::is_nothrow_move_constructible_v<T> && std::is_nothrow_default_constructible_v<T>);

 public:
  explicit MpmcQueue(std::size_t capacity)
      : capacity_{std::bit_ceil(capacity < 2 ? std::size_t{2} : capacity)},
        mask_{capacity_ - 1},
        cells_{std::make_unique<Cell[]>(capacity_)} {
    for (std::size_t i = 0; i < capacity_; ++i) {
      cells_[i].sequence.store(i, std::memory_order_relaxed);
    }
  }
  MpmcQueue(const MpmcQueue&) = delete;
  MpmcQueue& operator=(const MpmcQueue&) = delete;

  [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

  // [snippet:push]
  [[nodiscard]] bool try_push(T value) noexcept {
    std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
    for (;;) {
      Cell& cell = cells_[pos & mask_];
      const std::size_t seq = cell.sequence.load(std::memory_order_acquire);
      const auto diff = static_cast<std::intptr_t>(seq) - static_cast<std::intptr_t>(pos);
      if (diff == 0) {  // slot is free for position pos: try to claim it
        if (enqueue_pos_.compare_exchange_weak(pos, pos + 1, std::memory_order_relaxed)) {
          cell.value = std::move(value);
          cell.sequence.store(pos + 1, std::memory_order_release);  // ready for consumer
          return true;
        }
        // CAS failed: pos was reloaded, retry
      } else if (diff < 0) {
        return false;  // the slot still holds an unconsumed value: queue full
      } else {
        pos = enqueue_pos_.load(std::memory_order_relaxed);  // another producer won
      }
    }
  }
  // [/snippet:push]

  [[nodiscard]] std::optional<T> try_pop() noexcept {
    std::size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
    for (;;) {
      Cell& cell = cells_[pos & mask_];
      const std::size_t seq = cell.sequence.load(std::memory_order_acquire);
      const auto diff = static_cast<std::intptr_t>(seq) - static_cast<std::intptr_t>(pos + 1);
      if (diff == 0) {
        if (dequeue_pos_.compare_exchange_weak(pos, pos + 1, std::memory_order_relaxed)) {
          std::optional<T> out{std::move(cell.value)};
          cell.sequence.store(pos + capacity_, std::memory_order_release);  // free for next lap
          return out;
        }
      } else if (diff < 0) {
        return std::nullopt;  // empty
      } else {
        pos = dequeue_pos_.load(std::memory_order_relaxed);
      }
    }
  }

 private:
  struct alignas(cache_line_size) Cell {
    std::atomic<std::size_t> sequence{0};
    T value{};
  };
  const std::size_t capacity_;
  const std::size_t mask_;
  std::unique_ptr<Cell[]> cells_;
  alignas(cache_line_size) std::atomic<std::size_t> enqueue_pos_{0};
  alignas(cache_line_size) std::atomic<std::size_t> dequeue_pos_{0};
};

}  // namespace minidaq
