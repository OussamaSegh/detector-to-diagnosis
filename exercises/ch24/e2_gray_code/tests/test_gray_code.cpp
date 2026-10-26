// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 24.2.
#include <gtest/gtest.h>

#include <cstdint>

#include "gray_code.hpp"

using namespace gray;

namespace {

// What a flip-flop in the other clock domain captures when the value changes from `before` to
// `after` during its sampling window: each bit that changes may be caught old or new. `take` says
// which of the changing bits are caught new.
std::uint32_t torn(std::uint32_t before, std::uint32_t after, std::uint32_t take) {
  const std::uint32_t changing = before ^ after;
  return before ^ (changing & take);
}

}  // namespace

TEST(GrayCode, KnownValues) {
  EXPECT_EQ(encode(0), 0U);
  EXPECT_EQ(encode(1), 1U);
  EXPECT_EQ(encode(2), 3U);
  EXPECT_EQ(encode(3), 2U);
  EXPECT_EQ(encode(7), 4U);
  EXPECT_EQ(encode(8), 12U);
  constexpr std::uint32_t at_compile_time = encode(4);
  EXPECT_EQ(at_compile_time, 6U);
}

TEST(GrayCode, DecodeUndoesEncode) {
  for (std::uint32_t b = 0; b < (1U << 16); ++b) {
    ASSERT_EQ(decode(encode(b)), b) << b;
  }
  for (const std::uint32_t b : {0xFFFF'FFFFU, 0x8000'0000U, 0xDEAD'BEEFU}) {
    EXPECT_EQ(decode(encode(b)), b);
  }
}

TEST(GrayCode, OneBitChangesPerStepAlsoWhenThePointerWraps) {
  for (const unsigned bits : {4U, 13U}) {  // a 13-bit pointer: a FIFO of 4,096 words
    const std::uint32_t mask = (1U << bits) - 1U;
    for (std::uint32_t b = 0; b <= mask; ++b) {
      const std::uint32_t next = (b + 1U) & mask;
      ASSERT_EQ(bits_changed(encode(b), encode(next)), 1) << b;
    }
  }
  EXPECT_EQ(bits_changed(0x7, 0x8), 4) << "binary 7 to 8 changes four bits at once";
}

TEST(GrayCode, ATornSampleIsTheOldOrTheNewValue) {
  // Binary: a pointer sampled while it goes from 7 to 8 can read as anything from 0 to 15.
  int wrong = 0;
  for (std::uint32_t take = 0; take < 16; ++take) {
    const std::uint32_t seen = torn(7, 8, take);
    wrong += seen != 7 && seen != 8 ? 1 : 0;
  }
  EXPECT_EQ(wrong, 14);
  // Gray: only one bit changes, so every sample is one of the two.
  for (std::uint32_t b = 0; b < 4096; ++b) {
    for (const std::uint32_t take : {0U, 0xFFFF'FFFFU}) {
      const std::uint32_t seen = decode(torn(encode(b), encode(b + 1), take));
      ASSERT_TRUE(seen == b || seen == b + 1) << b;
    }
  }
}

TEST(GrayCode, TheReadSideSeesHowManyWordsItMayRead) {
  constexpr unsigned depth_log2 = 12;  // 4,096 words, 13-bit pointers
  EXPECT_EQ(readable(encode(0), 0, depth_log2), 0U) << "empty";
  EXPECT_EQ(readable(encode(100), 40, depth_log2), 60U);
  EXPECT_EQ(readable(encode(4096), 0, depth_log2), 4096U)
      << "full: the pointers differ in the top bit";
  // Both pointers have wrapped past 2^13: the difference still counts the words.
  EXPECT_EQ(readable(encode(5), 8190, depth_log2), 7U);
  // A write pointer that is a cycle late is safe: the read side sees fewer words, never more.
  EXPECT_EQ(readable(encode(99), 40, depth_log2), 59U);
}
