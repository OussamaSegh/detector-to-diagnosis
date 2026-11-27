#include <gtest/gtest.h>

#include <stdexcept>
#include <utility>

#include "counted.hpp"
#include "run_log.hpp"

using ex::Live;
using ex::RunLog;

TEST(RunLog, HoldsHeaderAndIndex) {
  RunLog log{42, "phantom, 20 MBq", 2};
  EXPECT_EQ(log.run(), 42);
  EXPECT_EQ(log.note(), "phantom, 20 MBq");
  EXPECT_TRUE(log.add_block(0));
  EXPECT_TRUE(log.add_block(4096));
  EXPECT_FALSE(log.add_block(8192));
  EXPECT_EQ(log.blocks(), 2U);
}

TEST(RunLog, FreesEverythingOnTheNormalPath) {
  const long h = Live::headers();
  const long i = Live::indexes();
  { RunLog log{1, "a", 4}; }
  EXPECT_EQ(Live::headers(), h);
  EXPECT_EQ(Live::indexes(), i);
}

TEST(RunLog, ZeroCapacityThrowsAndLeaksNothing) {
  const long h = Live::headers();
  const long i = Live::indexes();
  EXPECT_THROW((RunLog{7, "bad configuration", 0}), std::invalid_argument);
  EXPECT_EQ(Live::headers(), h) << "the header built before the index threw was never freed";
  EXPECT_EQ(Live::indexes(), i);
}

TEST(RunLog, CopiesAreIndependentAndFreed) {
  const long h = Live::headers();
  {
    RunLog a{3, "x", 2};
    RunLog b = a;  // the recorded change copies two pointers here, and frees them twice
    b.add_block(1);
    EXPECT_EQ(a.blocks(), 0U);
    EXPECT_EQ(b.blocks(), 1U);
  }
  EXPECT_EQ(Live::headers(), h);
}

TEST(RunLog, MovesLeaveNoDoubleOwner) {
  const long h = Live::headers();
  {
    RunLog a{4, "y", 2};
    RunLog b = std::move(a);
    EXPECT_EQ(b.run(), 4);
  }
  EXPECT_EQ(Live::headers(), h);
}
