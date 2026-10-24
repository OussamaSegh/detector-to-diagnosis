// SPDX-License-Identifier: MIT
// Proves that the hot-path decoder never allocates: this test binary replaces
// the global allocation functions with counting versions.
#include <gtest/gtest.h>

#include <atomic>
#include <cstdlib>
#include <new>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"

namespace {
std::atomic<std::size_t> g_allocations{0};
}

void* operator new(std::size_t n) {
  g_allocations.fetch_add(1, std::memory_order_relaxed);
  if (void* p = std::malloc(n == 0 ? 1 : n)) {
    return p;
  }
  throw std::bad_alloc{};
}
// GCC cannot see that our operator new allocates with malloc, so it reports
// free() here as a new/delete mismatch. The pairing is correct by construction.
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmismatched-new-delete"
#endif
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif

using namespace minidaq;

// [snippet:test]
TEST(ZeroAllocation, StreamDecoderDoesNotAllocate) {
  // REQ: SRS-PERF-001
  std::vector<std::uint64_t> words(100'000);
  for (std::size_t i = 0; i < words.size(); ++i) {
    words[i] = packed::pack({static_cast<std::uint32_t>(i % 18432), 1022, i * 1000});
  }
  std::vector<Single> out(words.size());
  packed::StreamDecoder d{ScannerGeometry::num_crystals};
  const std::size_t before = g_allocations.load();
  const std::size_t n = d.decode(words, out);
  const std::size_t after = g_allocations.load();
  EXPECT_EQ(n, words.size());
  EXPECT_EQ(after - before, 0U);
}
// [/snippet:test]
