#include <gtest/gtest.h>

#include <atomic>
#include <cstdlib>
#include <new>
#include <vector>

#include "stage.hpp"

// ASan and TSan both supply their own operator new, so the counting
// replacement below cannot be linked into sanitizer builds.
#if defined(__SANITIZE_ADDRESS__) || defined(__SANITIZE_THREAD__)
#define EX_SANITIZED 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer) || __has_feature(thread_sanitizer)
#define EX_SANITIZED 1
#endif
#endif

#ifndef EX_SANITIZED
namespace {
std::atomic<std::size_t> g_news{0};
}

void* operator new(std::size_t n) {
  g_news.fetch_add(1, std::memory_order_relaxed);
  if (void* p = std::malloc(n == 0 ? 1 : n)) {
    return p;
  }
  throw std::bad_alloc{};
}
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmismatched-new-delete"
#endif
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif
#endif

namespace {
std::vector<ex::Single> batch(std::size_t n, int seed) {
  std::vector<ex::Single> v(n);
  for (std::size_t i = 0; i < n; ++i) {
    v[i] = ex::Single{static_cast<std::int64_t>(i), static_cast<std::uint32_t>(i),
                      300.0F + static_cast<float>((i * 37 + static_cast<std::size_t>(seed)) % 400)};
  }
  return v;
}
}  // namespace

TEST(Stage, FiltersInOrder) {
  ex::EnergyWindowStage st{435.0F, 587.0F, 1024};
  const auto in = batch(1000, 1);
  const auto r = st.process(in);
  ASSERT_TRUE(r);
  std::size_t expected = 0;
  std::int64_t last = -1;
  for (const auto& s : in) {
    expected += (s.energy_kev >= 435.0F && s.energy_kev <= 587.0F) ? 1U : 0U;
  }
  EXPECT_EQ(r->size(), expected);
  for (const auto& s : *r) {
    EXPECT_GE(s.energy_kev, 435.0F);
    EXPECT_LE(s.energy_kev, 587.0F);
    EXPECT_GT(s.time_ps, last);
    last = s.time_ps;
  }
}

TEST(Stage, SteadyStateDoesNotAllocate) {
#ifdef EX_SANITIZED
  GTEST_SKIP() << "allocation counting is disabled under ASan/TSan";
#else
  ex::EnergyWindowStage st{435.0F, 587.0F, 4096};
  const auto in = batch(4096, 2);
  ASSERT_TRUE(st.process(in));  // warm-up
  const std::size_t before = g_news.load();
  std::size_t kept = 0;
  for (int i = 0; i < 1000; ++i) {
    auto r = st.process(in);
    ASSERT_TRUE(r);
    kept += r->size();
  }
  EXPECT_EQ(g_news.load() - before, 0U);
  EXPECT_GT(kept, 0U);
#endif
}

TEST(Stage, RejectsOversizedBatch) {
  ex::EnergyWindowStage st{435.0F, 587.0F, 128};
  const auto in = batch(129, 3);
  const auto r = st.process(in);
  ASSERT_FALSE(r);
  EXPECT_EQ(r.error(), ex::StageError::batch_too_large);
}
