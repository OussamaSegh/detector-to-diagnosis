// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "tdc_word.hpp"

using namespace ex91;

TEST(TdcWord, FieldsAndUnits) {
  HitDecoder d;
  const auto h = d.decode(make_hit(1023, 3, 7));
  ASSERT_TRUE(h);
  EXPECT_EQ(h->channel, 1023);
  EXPECT_EQ(h->time_ps, 3 * 5120 + 7 * 5) << "coarse ticks of 5120 ps, fine bins of 5 ps";
  EXPECT_EQ(wrap_period_ps, 5'629'499'534'213'120) << "about 94 minutes";
}

TEST(TdcWord, LargestTimeDoesNotOverflow) {
  HitDecoder d;
  const auto h = d.decode(make_hit(0, (std::uint64_t{1} << 40) - 1, 1023));
  ASSERT_TRUE(h);
  EXPECT_EQ(h->time_ps, wrap_period_ps - 5);
}

TEST(TdcWord, OtherWordTypesAreSkippedAndCounted) {
  HitDecoder d;
  EXPECT_FALSE(d.decode(std::uint64_t{0x8} << 60));  // e.g. a status word
  EXPECT_FALSE(d.decode(0));
  EXPECT_TRUE(d.decode(make_hit(5, 10, 0)));
  EXPECT_EQ(d.stats().other_words, 2U);
  EXPECT_EQ(d.stats().hits, 1U);
}

TEST(TdcWord, AWrapIsUndone) {
  HitDecoder d;
  const std::uint64_t last = (std::uint64_t{1} << 40) - 1;
  const auto a = d.decode(make_hit(1, last, 1000));
  const auto b = d.decode(make_hit(1, 0, 20));  // 1 tick and a bit later, after the wrap
  ASSERT_TRUE(a && b);
  EXPECT_EQ(b->time_ps - a->time_ps, 5120 - 1000 * 5 + 20 * 5);
  EXPECT_EQ(d.stats().wraps, 1U);
}

TEST(TdcWord, ALateWordIsNotAWrap) {
  HitDecoder d;
  const auto a = d.decode(make_hit(1, 1'000'000, 0));
  const auto late = d.decode(make_hit(2, 999'000, 0));  // 5 us late
  const auto c = d.decode(make_hit(1, 1'000'001, 0));
  ASSERT_TRUE(a && late && c);
  EXPECT_EQ(late->time_ps, std::int64_t{999'000} * 5120) << "earlier than a, not 94 minutes later";
  EXPECT_EQ(c->time_ps - a->time_ps, 5120);
  EXPECT_EQ(d.stats().wraps, 0U);
}

TEST(TdcWord, ALateWordFromBeforeTheWrap) {
  HitDecoder d;
  const std::uint64_t last = (std::uint64_t{1} << 40) - 1;
  const auto before = d.decode(make_hit(1, last - 10, 0));
  const auto after = d.decode(make_hit(1, 5, 0));    // wrapped
  const auto late = d.decode(make_hit(2, last - 2, 0));  // arrives after, happened before the wrap
  ASSERT_TRUE(before && after && late);
  EXPECT_LT(late->time_ps, after->time_ps);
  EXPECT_EQ(late->time_ps - before->time_ps, 8 * 5120);
  EXPECT_EQ(d.stats().wraps, 1U);
}

TEST(TdcWord, ThreeHoursOfData) {
  // One hit every 1.3 s for 2.9 hours: the time stays monotonic across the wrap.
  HitDecoder d;
  std::vector<std::uint64_t> words;
  const std::uint64_t mask = (std::uint64_t{1} << 50) - 1;
  for (std::uint64_t i = 0; i < 8000; ++i) {
    const std::uint64_t code = (i * 263'000'000'001ULL) & mask;  // ~1.3 s per step in 5 ps units
    words.push_back(make_hit(static_cast<std::uint16_t>(i % 2), code >> 10, code & 0x3FF));
  }
  std::int64_t prev = -1;
  for (std::size_t i = 0; i < words.size(); ++i) {
    const auto h = d.decode(words[i]);
    ASSERT_TRUE(h);
    EXPECT_GT(h->time_ps, prev) << "word " << i;
    prev = h->time_ps;
  }
  EXPECT_EQ(d.stats().wraps, 1U) << "8000 * 1.3 s = 2.9 h: one wrap after 94 minutes";
}
