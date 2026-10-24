// SPDX-License-Identifier: MIT
// Exercise 4.4: an arena whose pages are faulted in up front.
#pragma once

#include <cstddef>

namespace ex {

class PrefaultedArena {
 public:
  struct Options {
    bool lock = false;        // mlock the region (best effort, see locked())
    bool huge_pages = false;  // MADV_HUGEPAGE instead of MADV_NOHUGEPAGE
  };

  explicit PrefaultedArena(std::size_t bytes, Options options);
  explicit PrefaultedArena(std::size_t bytes) : PrefaultedArena(bytes, Options{}) {}
  ~PrefaultedArena();
  PrefaultedArena(PrefaultedArena&& other) noexcept;
  PrefaultedArena& operator=(PrefaultedArena&& other) noexcept;
  PrefaultedArena(const PrefaultedArena&) = delete;
  PrefaultedArena& operator=(const PrefaultedArena&) = delete;

  // nullptr if full or if align is not a power of two. Never faults, never locks.
  [[nodiscard]] void* allocate(std::size_t n, std::size_t align = alignof(std::max_align_t)) noexcept;
  void reset() noexcept { used_ = 0; }

  [[nodiscard]] std::size_t capacity() const noexcept { return size_; }
  [[nodiscard]] std::size_t used() const noexcept { return used_; }
  [[nodiscard]] bool locked() const noexcept { return locked_; }
  [[nodiscard]] const void* data() const noexcept { return base_; }

 private:
  void release() noexcept;

  std::byte* base_ = nullptr;
  std::size_t size_ = 0;
  std::size_t used_ = 0;
  bool locked_ = false;
};

}  // namespace ex
