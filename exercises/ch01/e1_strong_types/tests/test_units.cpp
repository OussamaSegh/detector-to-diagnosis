#include <gtest/gtest.h>

#include <cstdint>
#include <functional>
#include <type_traits>

#include "units.hpp"

using ex::KeV;
using ex::Picoseconds;

TEST(StrongTypes, SameUnitArithmeticWorks) {
  const Picoseconds a{1000};
  const Picoseconds b{250};
  EXPECT_EQ(ex::count(a + b), 1250);
  EXPECT_EQ(ex::count(a - b), 750);
  EXPECT_EQ(ex::count(a * 3), 3000);
  EXPECT_FLOAT_EQ(ex::count(KeV{511.0F} - KeV{11.0F}), 500.0F);
  EXPECT_TRUE(b < a);
}

TEST(StrongTypes, DifferentUnitsDoNotMix) {
  EXPECT_FALSE((std::is_invocable_v<std::plus<>, Picoseconds, KeV>));
  EXPECT_FALSE((std::is_invocable_v<std::minus<>, KeV, Picoseconds>));
}

TEST(StrongTypes, RawNumbersDoNotSneakIn) {
  EXPECT_FALSE((std::is_invocable_v<std::plus<>, Picoseconds, std::int64_t>));
  EXPECT_FALSE((std::is_convertible_v<std::int64_t, Picoseconds>));
  EXPECT_FALSE((std::is_convertible_v<Picoseconds, std::int64_t>));
}

TEST(StrongTypes, ZeroCost) {
  EXPECT_EQ(sizeof(Picoseconds), sizeof(std::int64_t));
  EXPECT_EQ(sizeof(KeV), sizeof(float));
  EXPECT_TRUE(std::is_trivially_copyable_v<Picoseconds>);
  EXPECT_TRUE(std::is_trivially_copyable_v<KeV>);
}

TEST(StrongTypes, RatioIsDimensionless) {
  const Picoseconds window{4000};
  const Picoseconds tick{1000};
  const auto ratio = window / tick;
  EXPECT_TRUE((std::is_same_v<std::remove_cv_t<decltype(ratio)>, std::int64_t>));
  EXPECT_EQ(ratio, 4);
}
