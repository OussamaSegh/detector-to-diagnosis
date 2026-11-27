#include <gtest/gtest.h>

#include <type_traits>
#include <utility>
#include <vector>

#include "samples.hpp"

using ex::Samples;

namespace {
Samples ramp(std::size_t n) {
  Samples s{n};
  for (std::size_t i = 0; i < n; ++i) s[i] = static_cast<double>(i);
  return s;
}
}  // namespace

TEST(Samples, ConstructsZeroedWithOneAllocation) {
  const auto before = Samples::allocations();
  Samples s{4};
  EXPECT_EQ(s.size(), 4U);
  for (std::size_t i = 0; i < s.size(); ++i) EXPECT_EQ(s[i], 0.0);
  EXPECT_EQ(Samples::allocations(), before + 1);
}

TEST(Samples, EveryAllocationIsFreed) {
  const auto live = Samples::live();
  {
    Samples a = ramp(8);
    Samples b = a;
    Samples c = std::move(a);
    b = c;
    c = std::move(b);
  }
  EXPECT_EQ(Samples::live(), live);
}

TEST(Samples, CopyIsDeepAndAllocatesOnce) {
  Samples a = ramp(3);
  const auto before = Samples::allocations();
  Samples b = a;
  EXPECT_EQ(Samples::allocations(), before + 1);
  b[0] = 42.0;
  EXPECT_EQ(a[0], 0.0);
  EXPECT_EQ(b[1], 1.0);
}

TEST(Samples, CopyAssignmentIsDeepAndSurvivesSelfAssignment) {
  Samples a = ramp(3);
  Samples b{10};
  b = a;
  EXPECT_EQ(b.size(), 3U);
  b[2] = -1.0;
  EXPECT_EQ(a[2], 2.0);
  Samples& alias = b;
  b = alias;
  EXPECT_EQ(b.size(), 3U);
  EXPECT_EQ(b[2], -1.0);
}

TEST(Samples, MoveStealsWithoutAllocating) {
  Samples a = ramp(5);
  const auto before = Samples::allocations();
  Samples b = std::move(a);
  Samples c{1};
  const auto after_c = Samples::allocations();
  c = std::move(b);
  EXPECT_EQ(Samples::allocations(), after_c);
  EXPECT_EQ(after_c, before + 1);  // only c's own buffer
  EXPECT_EQ(c.size(), 5U);
  EXPECT_EQ(c[4], 4.0);
  EXPECT_EQ(a.size(), 0U);  // NOLINT(bugprone-use-after-move): moved-from is empty by contract
  EXPECT_EQ(b.size(), 0U);  // NOLINT(bugprone-use-after-move)
}

TEST(Samples, MovesAreNoexceptSoVectorMovesOnGrowth) {
  EXPECT_TRUE(std::is_nothrow_move_constructible_v<Samples>);
  EXPECT_TRUE(std::is_nothrow_move_assignable_v<Samples>);
  std::vector<Samples> v;
  v.push_back(ramp(100));
  const auto before = Samples::allocations();
  for (int i = 0; i < 16; ++i) v.emplace_back(1);  // the vector grows several times
  EXPECT_EQ(Samples::allocations(), before + 16);  // growth moved, never copied
}
