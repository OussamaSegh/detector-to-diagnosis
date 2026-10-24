// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <functional>
#include <type_traits>

#include "minidaq/core/ids.hpp"
#include "minidaq/core/single.hpp"
#include "minidaq/core/units.hpp"

using namespace minidaq;
using namespace minidaq::literals;

// Compile-time guarantees: these are the real tests of a strong type.
static_assert(std::is_invocable_v<std::plus<>, Picoseconds, Picoseconds>);
static_assert(!std::is_invocable_v<std::plus<>, Picoseconds, KeV>);
static_assert(!std::is_invocable_v<std::plus<>, Picoseconds, std::int64_t>);
static_assert(!std::is_convertible_v<std::int64_t, Picoseconds>);  // explicit only
static_assert(!std::is_invocable_v<std::plus<>, CrystalId, CrystalId>);
static_assert(sizeof(Picoseconds) == sizeof(std::int64_t));
static_assert(std::is_trivially_copyable_v<KeV>);
static_assert(4_ns == Picoseconds{4000});
static_assert(2_us - 1_us == 1000_ns);

TEST(Quantity, SameUnitArithmetic) {
  // REQ: SRS-CORE-001
  constexpr Picoseconds window = 4_ns;
  EXPECT_EQ((window * 2).count(), 8000);
  EXPECT_EQ((window / 4).count(), 1000);
  EXPECT_EQ(window / 1_ns, 4);
  EXPECT_EQ(abs(1_ns - 3_ns), 2_ns);
}

TEST(Quantity, Ordering) {
  EXPECT_LT(1_ns, 2_ns);
  EXPECT_GT(KeV{511.0F}, KeV{350.0F});
  EXPECT_EQ(CrystalId{7}, CrystalId{7});
  EXPECT_NE(CrystalId{7}, CrystalId{8});
}

TEST(Coincidence, TimeDifferenceIsSecondMinusFirst) {
  const Coincidence c{Single{10_ns, CrystalId{1}, 511.0_keV}, Single{12_ns, CrystalId{200}, 500.0_keV},
                      CoincidenceKind::prompt};
  EXPECT_EQ(c.time_difference(), 2_ns);
}
