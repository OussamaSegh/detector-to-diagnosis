// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>
#include <sys/mman.h>
#include <unistd.h>

#include <cstdint>
#include <cstring>
#include <utility>

#include "minidaq/rt/realtime.hpp"
#include "prefaulted_arena.hpp"

#if defined(__SANITIZE_ADDRESS__) || defined(__SANITIZE_THREAD__)
#define EX_SANITIZED 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer) || __has_feature(thread_sanitizer)
#define EX_SANITIZED 1
#endif
#endif

namespace {

constexpr std::size_t mib = std::size_t{1} << 20;

std::int64_t faults_while(auto&& fn) {
  const auto before = minidaq::rt::thread_page_faults().minor;
  fn();
  return minidaq::rt::thread_page_faults().minor - before;
}

}  // namespace

TEST(PrefaultedArena, BumpAllocationRules) {
  ex::PrefaultedArena a{10'000};
  const auto page = static_cast<std::size_t>(::sysconf(_SC_PAGESIZE));
  EXPECT_EQ(a.capacity() % page, 0U);
  EXPECT_GE(a.capacity(), 10'000U);
  auto* p1 = static_cast<std::byte*>(a.allocate(3, 1));
  auto* p2 = static_cast<std::byte*>(a.allocate(64, 64));
  ASSERT_NE(p1, nullptr);
  ASSERT_NE(p2, nullptr);
  EXPECT_EQ(reinterpret_cast<std::uintptr_t>(p2) % 64, 0U);
  EXPECT_GE(p2, p1 + 3);
  EXPECT_EQ(a.allocate(1, 3), nullptr);  // not a power of two
  EXPECT_EQ(a.allocate(1, 0), nullptr);
  EXPECT_EQ(a.allocate(a.capacity(), 1), nullptr);  // does not fit any more
  a.reset();
  EXPECT_EQ(a.used(), 0U);
  EXPECT_NE(a.allocate(a.capacity(), 1), nullptr);  // the whole arena, exactly
  EXPECT_EQ(a.allocate(1, 1), nullptr);
}

TEST(PrefaultedArena, MoveTransfersOwnership) {
  ex::PrefaultedArena a{4096};
  const void* data = a.data();
  ASSERT_NE(data, nullptr);
  ex::PrefaultedArena b{std::move(a)};
  EXPECT_EQ(b.data(), data);
  EXPECT_EQ(a.allocate(1, 1), nullptr);  // NOLINT(bugprone-use-after-move): moved-from is empty
  ex::PrefaultedArena c{4096};
  c = std::move(b);
  EXPECT_EQ(c.data(), data);
}

TEST(PrefaultedArena, LockIsBestEffort) {
  ex::PrefaultedArena a{mib, {.lock = true, .huge_pages = false}};
  ASSERT_NE(a.data(), nullptr);
  if (!a.locked()) {
    GTEST_SKIP() << "mlock not permitted here (RLIMIT_MEMLOCK / CAP_IPC_LOCK)";
  }
  EXPECT_NE(a.allocate(mib, 1), nullptr);
}

TEST(PrefaultedArena, WritingAfterConstructionDoesNotFault) {
#ifdef EX_SANITIZED
  GTEST_SKIP() << "sanitizer shadow memory faults on its own";
#else
  constexpr std::size_t size = 32 * mib;
  const auto page = static_cast<std::size_t>(::sysconf(_SC_PAGESIZE));

  // Baseline: the same writes to plain, untouched anonymous memory.
  void* raw = ::mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  ASSERT_NE(raw, MAP_FAILED);
  (void)::madvise(raw, size, MADV_NOHUGEPAGE);
  const auto plain = faults_while([&] { std::memset(raw, 1, size); });
  ::munmap(raw, size);
  EXPECT_GT(plain, static_cast<std::int64_t>(size / page / 2)) << "baseline should fault about once per page";

  ex::PrefaultedArena arena{size};
  void* p = arena.allocate(size, 1);
  ASSERT_NE(p, nullptr);
  const auto prefaulted = faults_while([&] { std::memset(p, 1, size); });
  EXPECT_LT(prefaulted, 64) << "plain mmap took " << plain << " faults";
  RecordProperty("plain_faults", static_cast<int>(plain));
  RecordProperty("prefaulted_faults", static_cast<int>(prefaulted));
#endif
}
