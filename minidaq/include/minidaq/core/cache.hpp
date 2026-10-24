// SPDX-License-Identifier: MIT
// MiniDAQ - cache line size for padding and alignment (Chapters 2 and 3).
//
// std::hardware_destructive_interference_size (C++17, <new>) is the portable
// name for "keep these apart to avoid false sharing". In practice:
//  - GCC defines it, but warns (-Winterference-size) when it is used in a
//    header, because its value may differ between -mtune targets and would
//    then change struct layout across translation units (an ABI hazard).
//  - Clang with libstdc++ does not provide it at all before Clang 19.
// MiniDAQ therefore uses a fixed 64 bytes, correct for current x86-64 and most
// ARMv8 server cores. (Apple M-series cores use 128-byte lines; Intel's
// adjacent-line prefetcher also makes 128 bytes a safer padding on x86 when
// memory is not tight.)
#pragma once

#include <cstddef>

namespace minidaq {

// [snippet:padding]
inline constexpr std::size_t cache_line_size = 64;

// Wraps a value so that it occupies its own cache line.
template <typename T>
struct alignas(cache_line_size) CacheAligned {
  T value{};
};
// [/snippet:padding]

}  // namespace minidaq
