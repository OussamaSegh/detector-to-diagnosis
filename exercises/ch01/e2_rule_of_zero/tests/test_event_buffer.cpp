#include <gtest/gtest.h>

#include <span>
#include <type_traits>
#include <utility>

#include "event_buffer.hpp"

using ex::EventBuffer;
using ex::Single;

TEST(EventBuffer, PushUntilFull) {
  EventBuffer b{3};
  EXPECT_TRUE(b.push({1, 10, 511.0F}));
  EXPECT_TRUE(b.push({2, 11, 500.0F}));
  EXPECT_TRUE(b.push({3, 12, 450.0F}));
  EXPECT_FALSE(b.push({4, 13, 400.0F}));
  EXPECT_EQ(b.size(), 3U);
  EXPECT_EQ(b.capacity(), 3U);
}

TEST(EventBuffer, ViewCoversExactlyTheStoredEvents) {
  EventBuffer b{8};
  b.push({1, 10, 511.0F});
  b.push({2, 11, 500.0F});
  std::span<const Single> v = b.view();
  ASSERT_EQ(v.size(), 2U);
  EXPECT_EQ(v[1].time_ps, 2);
}

TEST(EventBuffer, CopyIsDeep) {
  EventBuffer a{4};
  a.push({1, 10, 511.0F});
  {
    EventBuffer c = a;  // starter: shallow copy, double free at end of scope
    c.push({2, 11, 500.0F});
    EXPECT_EQ(c.size(), 2U);
  }
  EXPECT_EQ(a.size(), 1U);
  EXPECT_EQ(a.view()[0].crystal, 10U);
}

TEST(EventBuffer, CopyAssignIsDeep) {
  EventBuffer a{2};
  a.push({1, 1, 1.0F});
  EventBuffer b{5};
  b = a;
  b.push({2, 2, 2.0F});
  EXPECT_EQ(a.size(), 1U);
  EXPECT_EQ(b.size(), 2U);
}

TEST(EventBuffer, MoveIsNoexceptAndEmptiesSource) {
  EXPECT_TRUE(std::is_nothrow_move_constructible_v<EventBuffer>);
  EXPECT_TRUE(std::is_nothrow_move_assignable_v<EventBuffer>);
  EventBuffer a{4};
  a.push({1, 10, 511.0F});
  EventBuffer m = std::move(a);
  EXPECT_EQ(m.size(), 1U);
  EXPECT_EQ(a.size(), 0U);       // NOLINT(bugprone-use-after-move): valid but unspecified is not enough here
  EXPECT_EQ(a.capacity(), 0U);   // NOLINT(bugprone-use-after-move)
  EXPECT_FALSE(a.push({9, 9, 9.0F}));  // NOLINT(bugprone-use-after-move)
}
