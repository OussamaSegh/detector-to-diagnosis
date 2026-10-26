// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 23.3, with the numbers Chapter 23 measured on the loopback
// interface: a 1,472-byte datagram is charged 2,305 bytes, an 8,208-byte one 16,644.
#include <gtest/gtest.h>

#include "buffer_sizing.hpp"

using namespace sizing;

TEST(BufferSizing, TheKernelCapsTheRequest) {
  EXPECT_EQ(granted(8u << 20, 4u << 20), 4u << 20);
  EXPECT_EQ(granted(65'536, 4u << 20), 65'536U);
}

TEST(BufferSizing, CapacityMatchesTheMeasurements) {
  // Measured: 3,640, 910, 126 and 504 datagrams queued. The estimate may be one short.
  EXPECT_EQ(capacity(4'194'304, 2'305), 3'639U);
  EXPECT_EQ(capacity(1'048'576, 2'305), 909U);
  EXPECT_EQ(capacity(1'048'576, 16'644), 126U);
  EXPECT_EQ(capacity(4'194'304, 16'644), 504U);
  EXPECT_EQ(capacity(1'000, 0), 0U);
}

TEST(BufferSizing, AStallTheBufferSurvives) {
  // Chapter 9's real-time link at 2 MBq: 4,923 datagrams per second of 1,472 bytes.
  const Link real_time{4'923, 2'305};
  EXPECT_NEAR(longest_stall_s(4'194'304, real_time), 0.739, 0.001);  // 3,639 datagrams
  EXPECT_NEAR(longest_stall_s(65'536, real_time), 0.0114, 0.0001);  // 56 datagrams
  // The same data sent as fast as the sender can: about 470,000 datagrams per second.
  const Link burst{470'000, 2'305};
  EXPECT_NEAR(longest_stall_s(4'194'304, burst) * 1e3, 7.74, 0.01);
  EXPECT_EQ(longest_stall_s(4'194'304, Link{0, 2'305}), 0.0);
}

TEST(BufferSizing, TheSmallestRequestForAStall) {
  const Link link{100'000, 2'305};
  const auto r = request_for(0.010, link, 4u << 20);  // 10 ms: 1,000 datagrams
  ASSERT_TRUE(r);
  EXPECT_GE(capacity(*r, link.charged_bytes), 1'000U);
  EXPECT_LT(capacity(*r - 1, link.charged_bytes), 1'000U) << "and not a byte more";
  EXPECT_FALSE(request_for(0.100, link, 4u << 20)) << "100 ms needs more than rmem_max allows";
  EXPECT_TRUE(request_for(0.100, link, 16u << 20));
}
