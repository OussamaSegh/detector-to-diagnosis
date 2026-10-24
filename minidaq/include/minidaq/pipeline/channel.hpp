// SPDX-License-Identifier: MIT
// MiniDAQ - batches and channels between pipeline stages (Chapter 3).
//
// A Channel<T> connects one producer stage to one consumer stage. It owns a
// fixed pool of batches allocated at construction; batches circulate:
//
//   producer: acquire() empty batch -> fill -> publish()
//   consumer: receive() full batch  -> process -> release()
//
// Two SPSC rings carry batch pointers forward (full) and back (empty), so no
// memory is allocated after start-up, and a full pipeline shows up as "no
// empty batch available" at the producer: that is where back-pressure or the
// drop policy acts.
#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <utility>
#include <vector>

#include "minidaq/pipeline/spsc_ring.hpp"

namespace minidaq {

template <typename T>
struct Batch {
  explicit Batch(std::size_t capacity) : items(capacity) {}
  std::vector<T> items;  // fixed capacity; only the first `size` are valid
  std::size_t size = 0;
  std::uint64_t sequence = 0;  // batch number, for gap detection downstream

  [[nodiscard]] std::span<T> view() noexcept { return {items.data(), size}; }
  [[nodiscard]] std::span<const T> view() const noexcept { return {items.data(), size}; }
  [[nodiscard]] std::size_t capacity() const noexcept { return items.size(); }
  [[nodiscard]] bool full() const noexcept { return size == items.size(); }
  void clear() noexcept { size = 0; }
  void push_unchecked(const T& v) noexcept { items[size++] = v; }
};

template <typename T>
class Channel {
 public:
  Channel(std::size_t num_batches, std::size_t batch_capacity)
      : full_{num_batches}, empty_{num_batches} {
    storage_.reserve(num_batches);
    for (std::size_t i = 0; i < num_batches; ++i) {
      storage_.push_back(std::make_unique<Batch<T>>(batch_capacity));
      [[maybe_unused]] const bool ok = empty_.try_push(storage_.back().get());
    }
  }

  // Producer side.
  [[nodiscard]] Batch<T>* acquire() noexcept {
    if (spare_ != nullptr) {  // a batch we acquired earlier but did not use
      return std::exchange(spare_, nullptr);
    }
    auto b = empty_.try_pop();
    if (!b) {
      return nullptr;
    }
    (*b)->clear();
    return *b;
  }
  void publish(Batch<T>* b) noexcept {
    b->sequence = next_sequence_++;
    // Cannot fail: the ring holds every batch the channel owns.
    [[maybe_unused]] const bool ok = full_.try_push(std::move(b));
  }
  // Producer gives back a batch it acquired but did not fill. It is kept on
  // the producer side: pushing it onto empty_ would make the producer a second
  // writer of a ring whose only writer is the consumer, breaking SPSC.
  void release_unused(Batch<T>* b) noexcept { spare_ = b; }
  void close() noexcept { closed_.store(true, std::memory_order_release); }

  // Consumer side.
  [[nodiscard]] Batch<T>* receive() noexcept {
    auto b = full_.try_pop();
    return b ? *b : nullptr;
  }
  void release(Batch<T>* b) noexcept { [[maybe_unused]] const bool ok = empty_.try_push(std::move(b)); }
  // True once the producer has closed the channel. Check receive() once more
  // after seeing closed(): batches published before close() may still be queued.
  [[nodiscard]] bool closed() const noexcept { return closed_.load(std::memory_order_acquire); }

  [[nodiscard]] std::size_t queued_approx() const noexcept { return full_.size_approx(); }
  [[nodiscard]] std::size_t num_batches() const noexcept { return storage_.size(); }

 private:
  std::vector<std::unique_ptr<Batch<T>>> storage_;
  SpscRing<Batch<T>*> full_;
  SpscRing<Batch<T>*> empty_;
  std::uint64_t next_sequence_ = 0;  // producer-only
  Batch<T>* spare_ = nullptr;        // producer-only
  std::atomic<bool> closed_{false};
};

}  // namespace minidaq
