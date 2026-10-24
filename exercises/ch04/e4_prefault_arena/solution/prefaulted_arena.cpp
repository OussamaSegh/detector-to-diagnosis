// SPDX-License-Identifier: MIT
// Exercise 4.4 solution.
#include "prefaulted_arena.hpp"

#include <sys/mman.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <system_error>
#include <utility>

namespace ex {

// [snippet:ctor]
PrefaultedArena::PrefaultedArena(std::size_t bytes, Options options) {
  const auto page = static_cast<std::size_t>(::sysconf(_SC_PAGESIZE));
  size_ = (std::max<std::size_t>(bytes, 1) + page - 1) / page * page;
  void* p = ::mmap(nullptr, size_, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) {
    throw std::system_error{errno, std::generic_category(), "mmap"};
  }
  base_ = static_cast<std::byte*>(p);
  // Advice is best effort: a kernel without THP support returns EINVAL.
  (void)::madvise(base_, size_, options.huge_pages ? MADV_HUGEPAGE : MADV_NOHUGEPAGE);
  // Write, do not read: a read of an untouched anonymous page maps the shared
  // zero page and the first real write would still fault.
  for (std::size_t off = 0; off < size_; off += page) {
    *static_cast<volatile std::byte*>(base_ + off) = std::byte{0};
  }
  if (options.lock) {
    locked_ = ::mlock(base_, size_) == 0;
  }
}
// [/snippet:ctor]

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
  if (align == 0 || (align & (align - 1)) != 0 || base_ == nullptr) {
    return nullptr;
  }
  const auto addr = reinterpret_cast<std::uintptr_t>(base_) + used_;
  const std::size_t pad = (align - addr % align) % align;
  if (pad > size_ - used_ || n > size_ - used_ - pad) {
    return nullptr;
  }
  void* out = base_ + used_ + pad;
  used_ += pad + n;
  return out;
}

void PrefaultedArena::release() noexcept {
  if (base_ != nullptr) {
    ::munmap(base_, size_);
    base_ = nullptr;
  }
}

}  // namespace ex
