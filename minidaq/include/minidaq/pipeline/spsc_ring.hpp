// SPDX-License-Identifier: MIT
// MiniDAQ - bounded single-producer single-consumer ring buffer (Chapter 3).
//
// Exactly one thread may call the producer functions (try_push, push_batch)
// and exactly one other thread the consumer functions (try_pop, pop_batch).
// Design (after Rigtorp's SPSCQueue and the classic Lamport queue):
//  - capacity is a power of two, indices grow without bound and are masked,
//    so "full" and "empty" are unambiguous without a wasted slot;
//  - head (consumer) and tail (producer) live on separate cache lines;
//  - each side keeps a cached copy of the other side's index and re-reads the
//    shared atomic only when the cache says the ring looks full/empty. This
//    removes most cross-core cache-line traffic.
// Memory ordering: the producer writes the slot, then publishes tail with a
// release store; the consumer reads tail with an acquire load before reading
// the slot. Symmetrically for head. No seq_cst is needed (see Chapter 3).
#pragma once

#include <atomic>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <type_traits>
#include <utility>

#include "minidaq/core/cache.hpp"

namespace minidaq {

template <typename T>
class SpscRing {
  static_assert(std::is_nothrow_move_constructible_v<T> && std::is_nothrow_move_assignable_v<T>,
                "ring elements must have noexcept moves");

 public:
  // capacity is rounded up to a power of two (minimum 2).
  explicit SpscRing(std::size_t capacity)
      : capacity_{std::bit_ceil(capacity < 2 ? std::size_t{2} : capacity)},
        mask_{capacity_ - 1},
        slots_{std::make_unique<T[]>(capacity_)} {}

  SpscRing(const SpscRing&) = delete;
  SpscRing& operator=(const SpscRing&) = delete;
  SpscRing(SpscRing&&) = delete;
  SpscRing& operator=(SpscRing&&) = delete;
  ~SpscRing() = default;

  [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

  // [snippet:push]
  // Producer: returns false if the ring is full (the value is not consumed).
  [[nodiscard]] bool try_push(T&& value) noexcept {
    const std::size_t tail = producer_.tail.load(std::memory_order_relaxed);  // only we write it
    if (tail - producer_.cached_head == capacity_) {
      producer_.cached_head = consumer_.head.load(std::memory_order_acquire);
      if (tail - producer_.cached_head == capacity_) {
        return false;
      }
    }
    slots_[tail & mask_] = std::move(value);
    producer_.tail.store(tail + 1, std::memory_order_release);  // publish the slot
    return true;
  }
  [[nodiscard]] bool try_push(const T& value) noexcept(std::is_nothrow_copy_constructible_v<T>) {
    T copy{value};
    return try_push(std::move(copy));
  }
  // [/snippet:push]

  // [snippet:pop]
  // Consumer: returns std::nullopt if the ring is empty.
  [[nodiscard]] std::optional<T> try_pop() noexcept {
    const std::size_t head = consumer_.head.load(std::memory_order_relaxed);  // only we write it
    if (head == consumer_.cached_tail) {
      consumer_.cached_tail = producer_.tail.load(std::memory_order_acquire);
      if (head == consumer_.cached_tail) {
        return std::nullopt;
      }
    }
    std::optional<T> out{std::move(slots_[head & mask_])};
    consumer_.head.store(head + 1, std::memory_order_release);  // hand the slot back
    return out;
  }
  // [/snippet:pop]

  // Producer: pushes as many elements of `in` as fit; returns how many.
  // One release store publishes the whole batch.
  [[nodiscard]] std::size_t push_batch(std::span<T> in) noexcept {
    const std::size_t tail = producer_.tail.load(std::memory_order_relaxed);
    std::size_t free = capacity_ - (tail - producer_.cached_head);
    if (free < in.size()) {
      producer_.cached_head = consumer_.head.load(std::memory_order_acquire);
      free = capacity_ - (tail - producer_.cached_head);
    }
    const std::size_t n = in.size() < free ? in.size() : free;
    for (std::size_t i = 0; i < n; ++i) {
      slots_[(tail + i) & mask_] = std::move(in[i]);
    }
    if (n > 0) {
      producer_.tail.store(tail + n, std::memory_order_release);
    }
    return n;
  }

  // Consumer: pops up to out.size() elements; returns how many.
  [[nodiscard]] std::size_t pop_batch(std::span<T> out) noexcept {
    const std::size_t head = consumer_.head.load(std::memory_order_relaxed);
    std::size_t avail = consumer_.cached_tail - head;
    if (avail < out.size()) {
      consumer_.cached_tail = producer_.tail.load(std::memory_order_acquire);
      avail = consumer_.cached_tail - head;
    }
    const std::size_t n = out.size() < avail ? out.size() : avail;
    for (std::size_t i = 0; i < n; ++i) {
      out[i] = std::move(slots_[(head + i) & mask_]);
    }
    if (n > 0) {
      consumer_.head.store(head + n, std::memory_order_release);
    }
    return n;
  }

  // Approximate fill level; safe to call from any thread (for monitoring only).
  [[nodiscard]] std::size_t size_approx() const noexcept {
    const std::size_t tail = producer_.tail.load(std::memory_order_acquire);
    const std::size_t head = consumer_.head.load(std::memory_order_acquire);
    return tail >= head ? tail - head : 0;
  }

 private:
  // [snippet:layout]
  struct alignas(cache_line_size) ProducerSide {
    std::atomic<std::size_t> tail{0};  // written by producer, read by consumer
    std::size_t cached_head{0};        // producer's private copy of head
  };
  struct alignas(cache_line_size) ConsumerSide {
    std::atomic<std::size_t> head{0};  // written by consumer, read by producer
    std::size_t cached_tail{0};        // consumer's private copy of tail
  };
  // [/snippet:layout]

  const std::size_t capacity_;
  const std::size_t mask_;
  std::unique_ptr<T[]> slots_;
  ProducerSide producer_;
  ConsumerSide consumer_;
};

}  // namespace minidaq
