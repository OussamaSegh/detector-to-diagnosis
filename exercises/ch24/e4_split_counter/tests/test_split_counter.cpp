// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 24.4: a board whose 64-bit counter advances between bus accesses,
// as a timestamp counter in the board's clock domain does while software reads it.
#include <gtest/gtest.h>

#include <cstdint>
#include <optional>

#include "split_counter.hpp"

using namespace split;

namespace {

constexpr std::uint32_t lo_addr = 0x50;
constexpr std::uint32_t hi_addr = 0x54;

class CountingBoard final : public Bus {
 public:
  CountingBoard(std::uint64_t start, std::uint64_t step) : value_{start}, step_{step} {}
  std::optional<std::uint32_t> read32(std::uint32_t address) override {
    ++accesses;
    if (fail_after && accesses > *fail_after) {
      return std::nullopt;
    }
    const std::uint64_t v = value_;
    value_ += step_;  // the counter moves on between any two accesses
    lowest_seen = lowest_seen ? *lowest_seen : v;
    highest_seen = v;
    if (address == lo_addr) {
      return static_cast<std::uint32_t>(v);
    }
    if (address == hi_addr) {
      return static_cast<std::uint32_t>(v >> 32U);
    }
    return 0U;
  }
  int accesses = 0;
  std::optional<int> fail_after;
  std::optional<std::uint64_t> lowest_seen;
  std::uint64_t highest_seen = 0;

 private:
  std::uint64_t value_;
  std::uint64_t step_;
};

}  // namespace

TEST(SplitCounter, ReadsACounterThatDoesNotCarry) {
  CountingBoard b{0x0000'0002'0000'1000ULL, 1};
  const auto v = read_counter(b, lo_addr, hi_addr);
  ASSERT_TRUE(v);
  EXPECT_EQ(*v >> 32U, 2U);
  EXPECT_GE(*v, *b.lowest_seen);
  EXPECT_LE(*v, b.highest_seen);
}

TEST(SplitCounter, NeverTearsAcrossACarry) {
  // The low half wraps during the read: reading each half once gives a value 2^32 away from the
  // truth in one direction or the other.
  for (std::uint64_t below = 0; below < 6; ++below) {
    CountingBoard b{0x0000'0007'FFFF'FFFFULL - below, 1};
    const auto v = read_counter(b, lo_addr, hi_addr);
    ASSERT_TRUE(v) << below;
    EXPECT_GE(*v, *b.lowest_seen) << below;
    EXPECT_LE(*v, b.highest_seen) << below;
  }
}

TEST(SplitCounter, GivesUpWhenTheHighHalfNeverHoldsStill) {
  CountingBoard b{0, std::uint64_t{1} << 32U};  // the high half changes at every access
  EXPECT_FALSE(read_counter(b, lo_addr, hi_addr, 4));
  EXPECT_EQ(b.accesses, 12) << "three accesses per attempt";
}

TEST(SplitCounter, AFailedReadIsNotAValue) {
  for (int n = 0; n < 3; ++n) {
    CountingBoard b{0x10, 1};
    b.fail_after = n;
    EXPECT_FALSE(read_counter(b, lo_addr, hi_addr)) << "fails after " << n << " accesses";
  }
}
