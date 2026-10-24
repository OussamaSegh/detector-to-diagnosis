// SPDX-License-Identifier: MIT
// Exercise 4.4 starter.
#include "prefaulted_arena.hpp"

#include <sys/mman.h>
#include <unistd.h>

#include <system_error>
#include <utility>

namespace ex {

PrefaultedArena::PrefaultedArena(std::size_t bytes, Options options) {
  // TODO: round up to pages, mmap, madvise, touch every page by writing, optionally mlock.
  (void)bytes;
  (void)options;
}

PrefaultedArena::~PrefaultedArena() { release(); }

PrefaultedArena::PrefaultedArena(PrefaultedArena&& other) noexcept
    : base_{std::exchange(other.base_, nullptr)},
      size_{std::exchange(other.size_, 0)},
      used_{std::exchange(other.used_, 0)},
      locked_{std::exchange(other.locked_, false)} {}

PrefaultedArena& PrefaultedArena::operator=(PrefaultedArena&& other) noexcept {
  if (this != &other) {
    release();
    base_ = std::exchange(other.base_, nullptr);
    size_ = std::exchange(other.size_, 0);
    used_ = std::exchange(other.used_, 0);
    locked_ = std::exchange(other.locked_, false);
  }
  return *this;
}

void* PrefaultedArena::allocate(std::size_t n, std::size_t align) noexcept {
  // TODO: bump allocation with alignment.
  (void)n;
  (void)align;
  return nullptr;
}

void PrefaultedArena::release() noexcept {
  if (base_ != nullptr) {
    ::munmap(base_, size_);
    base_ = nullptr;
  }
}

}  // namespace ex
