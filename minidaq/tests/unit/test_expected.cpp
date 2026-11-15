// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <type_traits>

#include "minidaq/core/expected.hpp"

using minidaq::Expected;
using minidaq::Unexpected;

namespace {
enum class Err { bad };
Expected<int, Err> half(int x) {
  if (x % 2 != 0) {
    return Unexpected{Err::bad};
  }
  return x / 2;
}
}  // namespace

TEST(Expected, ValueAndError) {
  auto ok = half(8);
  ASSERT_TRUE(ok);
  EXPECT_EQ(*ok, 4);
  auto bad = half(3);
  ASSERT_FALSE(bad);
  EXPECT_EQ(bad.error(), Err::bad);
  EXPECT_EQ(bad.value_or(-1), -1);
}

TEST(Expected, Monadic) {
  auto r = half(16).and_then(half).transform([](int v) { return v + 1; });
  ASSERT_TRUE(r);
  EXPECT_EQ(*r, 5);
  auto e = half(6).and_then(half);  // 3 is odd
  EXPECT_FALSE(e);
}

TEST(Expected, NonTrivialTypesAreDestroyed) {
  auto counter = std::make_shared<int>(0);
  {
    Expected<std::shared_ptr<int>, Err> a{counter};
    Expected<std::shared_ptr<int>, Err> b = a;
    EXPECT_EQ(counter.use_count(), 3);
    b = Expected<std::shared_ptr<int>, Err>{Unexpected{Err::bad}};
    EXPECT_EQ(counter.use_count(), 2);
  }
  EXPECT_EQ(counter.use_count(), 1);
}

TEST(Expected, StringValueMoves) {
  Expected<std::string, Err> s{std::string(100, 'x')};
  Expected<std::string, Err> t{std::move(s)};
  EXPECT_EQ(t->size(), 100U);
}

TEST(Expected, Void) {
  Expected<void, Err> ok;
  EXPECT_TRUE(ok);
  Expected<void, Err> bad{Unexpected{Err::bad}};
  EXPECT_FALSE(bad);
  EXPECT_EQ(bad.error(), Err::bad);
}

// CR-0028: every build is C++23 (GCC 13 reports 202100L, Clang 18 202302L), and
// Expected is std::expected exactly when the standard library provides it.
TEST(Expected, IsStdExpectedWhereverTheLibraryHasIt) {
  static_assert(__cplusplus > 202002L, "MiniDAQ is built as C++23 (ADR 0035)");
#if defined(__cpp_lib_expected) && __cpp_lib_expected >= 202202L
  static_assert(std::is_same_v<Expected<int, Err>, std::expected<int, Err>>);
  RecordProperty("implementation", "std::expected");
#else
  RecordProperty("implementation", "minidaq shim");
#endif
  SUCCEED();
}
