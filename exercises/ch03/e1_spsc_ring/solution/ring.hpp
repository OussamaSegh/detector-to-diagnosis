// SPDX-License-Identifier: MIT
// Exercise 3.1 solution: a lock-free SPSC ring of singles.
#pragma once

#include <atomic>
#include <bit>
#include <cstddef>
#include <memory>
#include <span>

#include "minidaq/core/cache.hpp"
#include "minidaq/core/single.hpp"

namespace ex {

using minidaq::Single;

class SinglesRing {
 public:
  explicit SinglesRing(std::size_t capacity)
      : cap_{std::bit_ceil(capacity < 2 ? std::size_t{2} : capacity)},
        mask_{cap_ - 1},
        slots_{std::make_unique<Single[]>(cap_)} {}

  [[nodiscard]] std::size_t capacity() const noexcept { return cap_; }

  // [snippet:pushpop]
  [[nodiscard]] bool try_push(const Single& s) noexcept {
    const std::size_t t = prod_.tail.load(std::memory_order_relaxed);
    if (t - prod_.head_cache == cap_) {
      prod_.head_cache = cons_.head.load(std::memory_order_acquire);
      if (t - prod_.head_cache == cap_) {
        return false;
      }
    }
    slots_[t & mask_] = s;
    prod_.tail.store(t + 1, std::memory_order_release);
    return true;
  }

  [[nodiscard]] bool try_pop(Single& out) noexcept {
    const std::size_t h = cons_.head.load(std::memory_order_relaxed);
    if (h == cons_.tail_cache) {
      cons_.tail_cache = prod_.tail.load(std::memory_order_acquire);
      if (h == cons_.tail_cache) {
        return false;
      }
    }
    out = slots_[h & mask_];
    cons_.head.store(h + 1, std::memory_order_release);
    return true;
  }
  // [/snippet:pushpop]

  [[nodiscard]] std::size_t try_push_n(std::span<const Single> in) noexcept {
    const std::size_t t = prod_.tail.load(std::memory_order_relaxed);
    if (cap_ - (t - prod_.head_cache) < in.size()) {
      prod_.head_cache = cons_.head.load(std::memory_order_acquire);
    }
    const std::size_t free = cap_ - (t - prod_.head_cache);
    const std::size_t n = in.size() < free ? in.size() : free;
    for (std::size_t i = 0; i < n; ++i) {
      slots_[(t + i) & mask_] = in[i];
    }
    if (n != 0) {
      prod_.tail.store(t + n, std::memory_order_release);
    }
    return n;
  }

  [[nodiscard]] std::size_t try_pop_n(std::span<Single> out) noexcept {
    const std::size_t h = cons_.head.load(std::memory_order_relaxed);
    if (cons_.tail_cache - h < out.size()) {
      cons_.tail_cache = prod_.tail.load(std::memory_order_acquire);
    }
    const std::size_t avail = cons_.tail_cache - h;
    const std::size_t n = out.size() < avail ? out.size() : avail;
    for (std::size_t i = 0; i < n; ++i) {
      out[i] = slots_[(h + i) & mask_];
    }
    if (n != 0) {
      cons_.head.store(h + n, std::memory_order_release);
    }
    return n;
  }

 private:
  struct alignas(minidaq::cache_line_size) Producer {
    std::atomic<std::size_t> tail{0};
    std::size_t head_cache{0};
  };
  struct alignas(minidaq::cache_line_size) Consumer {
    std::atomic<std::size_t> head{0};
    std::size_t tail_cache{0};
  };
  const std::size_t cap_;
  const std::size_t mask_;
  std::unique_ptr<Single[]> slots_;
  Producer prod_;
  Consumer cons_;
};

}  // namespace ex
