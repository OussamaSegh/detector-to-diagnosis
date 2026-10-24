// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdio>
#include <map>
#include <stdexcept>
#include <vector>

#include "pin_stages.hpp"

using minidaq::rt::SchedPolicy;

TEST(CpuList, ParsesSinglesRangesAndWhitespace) {
  EXPECT_EQ(ex::parse_cpu_list("0-2,5,7-8"), (std::vector<int>{0, 1, 2, 5, 7, 8}));
  EXPECT_EQ(ex::parse_cpu_list("3\n"), (std::vector<int>{3}));
  EXPECT_EQ(ex::parse_cpu_list("5,1-2,2"), (std::vector<int>{1, 2, 5}));  // sorted, unique
  EXPECT_EQ(ex::parse_cpu_list("4-4"), (std::vector<int>{4}));
  EXPECT_TRUE(ex::parse_cpu_list("").empty());
  EXPECT_TRUE(ex::parse_cpu_list("\n").empty());  // /sys/devices/system/cpu/isolated with nothing isolated
}

TEST(CpuList, RejectsMalformedLists) {
  for (const char* bad : {"3-1", "1,,2", "-1", "x", "1-", ",1", "1,", "1 2", "0x3"}) {
    EXPECT_THROW((void)ex::parse_cpu_list(bad), std::invalid_argument) << bad;
  }
}

TEST(Placement, FourCpusMatchesTheBookProfile) {
  const std::vector<int> cpus{0, 1, 2, 3};
  const auto p = ex::assign_stage_cpus(cpus);
  EXPECT_EQ(p.cpu, (std::array<int, 5>{1, 2, 3, 0, 0}));
  EXPECT_EQ(p.dedicated, (std::array<bool, 5>{true, true, true, false, false}));
}

TEST(Placement, FewerCpusShareTheHousekeepingCpu) {
  const std::vector<int> one{6};
  const auto p1 = ex::assign_stage_cpus(one);
  EXPECT_EQ(p1.cpu, (std::array<int, 5>{6, 6, 6, 6, 6}));
  EXPECT_EQ(p1.dedicated, (std::array<bool, 5>{}));
  const std::vector<int> two{0, 4};
  const auto p2 = ex::assign_stage_cpus(two);
  EXPECT_EQ(p2.cpu, (std::array<int, 5>{4, 0, 0, 0, 0}));
  EXPECT_EQ(p2.dedicated, (std::array<bool, 5>{true, false, false, false, false}));
}

TEST(Placement, ExtraCpusStayUnusedAndEmptyThrows) {
  const std::vector<int> five{2, 5, 7, 9, 11};
  const auto p = ex::assign_stage_cpus(five);
  EXPECT_EQ(p.cpu, (std::array<int, 5>{5, 7, 9, 2, 2}));
  EXPECT_THROW((void)ex::assign_stage_cpus(std::vector<int>{}), std::invalid_argument);
}

TEST(Profile, NeverTwoFifoStagesOnOneCpu) {
  for (int n = 1; n <= 8; ++n) {
    std::vector<int> cpus;
    for (int c = 0; c < n; ++c) {
      cpus.push_back(c);
    }
    const auto prof = ex::make_profile(ex::assign_stage_cpus(cpus), true);
    EXPECT_TRUE(prof.lock_memory);
    EXPECT_EQ(prof.prefault_stack_bytes, 256U * 1024U);
    std::map<int, int> fifo_per_cpu;
    int fifo_stages = 0;
    for (const auto& s : prof.stages) {
      EXPECT_GE(s.cpu, 0) << n << " CPUs: every stage must be pinned";
      if (s.policy == SchedPolicy::fifo) {
        ++fifo_per_cpu[s.cpu];
        ++fifo_stages;
        EXPECT_GE(s.priority, 1);
        EXPECT_LE(s.priority, 99);
      }
    }
    for (const auto& [cpu, count] : fifo_per_cpu) {
      EXPECT_EQ(count, 1) << n << " CPUs: CPU " << cpu;
    }
    EXPECT_EQ(fifo_stages, std::min(n - 1, 3)) << n << " CPUs";
  }
}

TEST(Profile, PinningOnlyKeepsTheNormalScheduler) {
  const std::vector<int> cpus{0, 1, 2, 3};
  const auto prof = ex::make_profile(ex::assign_stage_cpus(cpus), false);
  for (const auto& s : prof.stages) {
    EXPECT_EQ(s.policy, SchedPolicy::other);
  }
  EXPECT_EQ(prof.stages[0].cpu, 1);
}

TEST(Profile, RoundTripsThroughTheLibraryFormat) {
  const std::vector<int> cpus{0, 1, 2, 3};
  const auto prof = ex::make_profile(ex::assign_stage_cpus(cpus), true);
  EXPECT_EQ(prof.stages[0].priority, 80);
  const auto back = minidaq::rt::parse_profile(minidaq::rt::format_profile(prof));
  ASSERT_TRUE(back.has_value());
  EXPECT_EQ(*back, prof);
}

// Not an acceptance test: prints a profile for the CPUs this process may use.
TEST(Profile, PrintsProfileForThisMachine) {
  const auto cpus = ex::allowed_cpus();
  ASSERT_FALSE(cpus.empty());
  const auto prof = ex::make_profile(ex::assign_stage_cpus(cpus), true);
  std::printf("# generated for CPUs %d..%d\n%s", cpus.front(), cpus.back(),
              minidaq::rt::format_profile(prof).c_str());
}
