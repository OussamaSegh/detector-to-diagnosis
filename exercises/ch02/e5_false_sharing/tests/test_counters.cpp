#include <gtest/gtest.h>

#include <cstdint>
#include <cstdlib>
#include <thread>
#include <vector>

#include "counters.hpp"

TEST(Counters, StagesAreOnDifferentCacheLines) {
  ex::StageCounters c;
  for (std::size_t a = 0; a < ex::kStages; ++a) {
    for (std::size_t b = a + 1; b < ex::kStages; ++b) {
      const auto pa = reinterpret_cast<std::uintptr_t>(&c.stage(a));
      const auto pb = reinterpret_cast<std::uintptr_t>(&c.stage(b));
      const auto dist = pa > pb ? pa - pb : pb - pa;
      EXPECT_GE(dist, 64U) << "stages " << a << " and " << b;
    }
  }
}

TEST(Counters, ConcurrentIncrementsAreExact) {
  ex::StageCounters c;
  std::vector<std::thread> threads;
  for (std::size_t s = 0; s < ex::kStages; ++s) {
    threads.emplace_back([&c, s] {
      for (int i = 0; i < 200'000; ++i) {
        c.stage(s).events_in.fetch_add(1, std::memory_order_relaxed);
        c.stage(s).events_out.fetch_add(1, std::memory_order_relaxed);
      }
    });
  }
  for (auto& t : threads) {
    t.join();
  }
  for (std::size_t s = 0; s < ex::kStages; ++s) {
    EXPECT_EQ(c.stage(s).events_in.load(), 200'000U);
    EXPECT_EQ(c.stage(s).events_out.load(), 200'000U);
  }
}
