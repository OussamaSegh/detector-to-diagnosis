// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 24.3: the cycle model against a reference written as plainly as
// possible, on the same random stimulus as the SystemVerilog testbench hw/rtl/feb_out_fifo_tb.sv,
// and the sizing arithmetic with the numbers of Chapter 24.
#include <gtest/gtest.h>

#include <deque>
#include <random>

#include "out_fifo.hpp"

using namespace fifo;

TEST(OutFifo, KeepsTheOrderAndRefusesWhenFull) {
  OutFifo f{4};
  for (std::uint64_t w = 1; w <= 6; ++w) {
    EXPECT_FALSE(f.clock({true, true, w, false, false}));
  }
  EXPECT_EQ(f.level(), 4U);
  EXPECT_TRUE(f.overflow());
  EXPECT_EQ(f.lost(), 2U);
  // Full, and the link takes a word in the same cycle as an event: the event is still lost.
  EXPECT_EQ(f.clock({true, true, 7, true, false}), 1U);
  EXPECT_EQ(f.level(), 3U);
  EXPECT_EQ(f.lost(), 3U);
  for (std::uint64_t want : {2U, 3U, 4U}) {
    EXPECT_EQ(f.clock({false, false, 0, true, false}), want);
  }
  EXPECT_TRUE(f.empty());
  EXPECT_FALSE(f.clock({false, false, 0, true, false})) << "nothing to take";
}

TEST(OutFifo, NothingEntersWhileTheTriggersAreOff) {
  OutFifo f{4};
  EXPECT_FALSE(f.clock({false, true, 1, false, false}));
  EXPECT_TRUE(f.empty());
  EXPECT_FALSE(f.overflow());
}

TEST(OutFifo, ALostEventWinsOverAClearInTheSameCycle) {
  OutFifo f{1};
  f.clock({true, true, 1, false, false});
  f.clock({true, true, 2, false, true});  // lost, and software clears in the same cycle
  EXPECT_TRUE(f.overflow()) << "the loss must not be forgotten";
  f.clock({true, false, 0, false, true});
  EXPECT_FALSE(f.overflow());
}

TEST(OutFifo, MatchesAPlainModelOnRandomTraffic) {
  OutFifo f{8};
  std::deque<std::uint64_t> model;
  std::mt19937 rng{24};
  std::uniform_int_distribution<int> pct{0, 99};
  bool flag = false;
  std::uint64_t data = 0;
  std::uint64_t lost = 0;
  for (int cycle = 0; cycle < 20'000; ++cycle) {
    const int phase = (cycle / 2'500) % 4;  // slow link, fast link, fast link, triggers off
    const OutFifo::Inputs in{phase != 3, pct(rng) < (phase == 0 ? 60 : 30), ++data,
                             pct(rng) < (phase == 0 ? 25 : 70), pct(rng) < 5};
    std::optional<std::uint64_t> want;
    const bool event = in.in_valid && in.trigger_enable;
    const bool full = model.size() == 8;
    if (!model.empty() && in.out_ready) {
      want = model.front();
      model.pop_front();
    }
    if (event && !full) {
      model.push_back(in.in_data);
    }
    if (event && full) {
      flag = true;
      ++lost;
    } else if (in.overflow_clear) {
      flag = false;
    }
    ASSERT_EQ(f.clock(in), want) << "cycle " << cycle;
    ASSERT_EQ(f.level(), model.size()) << "cycle " << cycle;
    ASSERT_EQ(f.overflow(), flag) << "cycle " << cycle;
  }
  EXPECT_TRUE(f.empty()) << "the last phase drains it";
  EXPECT_EQ(f.lost(), lost);
  EXPECT_GT(lost, 0U) << "the traffic must fill the FIFO";
}

TEST(FifoSizing, TheNumbersOfChapter24) {
  // The board's FIFO: 4,096 words, a link of 25,000 words per second.
  EXPECT_NEAR(*time_to_full_s(4'096, 50'000, 25'000), 0.16384, 1e-9);
  EXPECT_NEAR(*time_to_full_s(4'096, 27'000, 25'000), 2.048, 1e-9);
  EXPECT_FALSE(time_to_full_s(4'096, 20'000, 25'000)) << "a faster link never fills";
  EXPECT_FALSE(time_to_full_s(4'096, 25'000, 25'000));
  EXPECT_NEAR(drain_time_s(4'096, 25'000), 0.16384, 1e-9);
  EXPECT_NEAR(drain_time_s(2'000, 25'000), 0.08, 1e-9);
  // A burst of 10 ms at 400,000 words per second over a link of 25,000: 3,750 words.
  EXPECT_EQ(depth_for_burst(400'000, 25'000, 0.010), 3'750U);
  EXPECT_EQ(depth_for_burst(400'000, 25'000, 0.0100001), 3'751U) << "round up";
  EXPECT_EQ(depth_for_burst(20'000, 25'000, 1.0), 1U);
}
