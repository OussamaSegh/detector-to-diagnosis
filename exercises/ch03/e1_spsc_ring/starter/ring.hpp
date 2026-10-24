// SPDX-License-Identifier: MIT
// Exercise 3.1 starter: a lock-free SPSC ring of singles.
#pragma once

#include <atomic>
#include <cstddef>
#include <memory>
#include <span>

#include "minidaq/core/cache.hpp"
#include "minidaq/core/single.hpp"

namespace ex {

using minidaq::Single;

class SinglesRing {
 public:
  // TODO: round capacity up to a power of two (minimum 2); allocate the slots.
  explicit SinglesRing(std::size_t capacity) {}

  [[nodiscard]] std::size_t capacity() const noexcept { return 0; }  // TODO

  // Producer thread only. Returns false if full.
  [[nodiscard]] bool try_push(const Single& s) noexcept {
    // TODO: 1. load your own index (which memory order is enough?)
    //       2. check for space, re-reading the consumer's index only if needed
    //       3. write the slot, then publish the new index (which order?)
    return false;
  }

  // Consumer thread only. Returns false if empty.
  [[nodiscard]] bool try_pop(Single& out) noexcept {
    // TODO: mirror image of try_push.
    return false;
  }

  // Producer: push up to in.size() singles; returns how many were pushed.
  [[nodiscard]] std::size_t try_push_n(std::span<const Single> in) noexcept { return 0; }  // TODO
  // Consumer: pop up to out.size() singles; returns how many were popped.
  [[nodiscard]] std::size_t try_pop_n(std::span<Single> out) noexcept { return 0; }  // TODO

 private:
  // TODO: choose the members. Think about which ones each thread writes, and
  // keep data written by different threads on different cache lines.
};

}  // namespace ex
