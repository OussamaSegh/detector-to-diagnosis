#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "processors.hpp"

namespace {
struct CountingSink {
  std::uint64_t n = 0;
  void consume(const ex::Single&) { ++n; }
  [[nodiscard]] std::uint64_t count() const { return n; }
};
struct NoCount {
  void consume(const ex::Single&) {}
};
struct WrongArg {
  void consume(int) {}
  [[nodiscard]] std::uint64_t count() const { return 0; }
};
struct EnergyWindow {
  float lo, hi;
  [[nodiscard]] bool accept(const ex::Single& s) const { return s.energy_kev >= lo && s.energy_kev <= hi; }
};
struct ReturnsInt {
  [[nodiscard]] int accept(const ex::Single&) const { return 1; }
};
}  // namespace

TEST(Concepts, SinkConcept) {
  EXPECT_TRUE(ex::is_sink_v<CountingSink>);
  EXPECT_FALSE(ex::is_sink_v<NoCount>);
  EXPECT_FALSE(ex::is_sink_v<WrongArg>);
  EXPECT_FALSE(ex::is_sink_v<int>);
}

TEST(Concepts, FilterConcept) {
  EXPECT_TRUE(ex::is_filter_v<EnergyWindow>);
  EXPECT_FALSE(ex::is_filter_v<ReturnsInt>);  // must return exactly bool
  EXPECT_FALSE(ex::is_filter_v<CountingSink>);
}

TEST(Concepts, FeedAppliesTheFilter) {
  const std::vector<ex::Single> in = {{1, 1, 200.0F}, {2, 2, 350.0F}, {3, 3, 511.0F}, {4, 4, 650.0F}, {5, 5, 700.0F}};
  EnergyWindow w{350.0F, 650.0F};
  CountingSink sink;
  EXPECT_EQ(ex::feed(in, w, sink), 3U);
  EXPECT_EQ(sink.count(), 3U);
}
