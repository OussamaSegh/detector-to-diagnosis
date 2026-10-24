// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <thread>

#include "minidaq/rt/realtime.hpp"

namespace rt = minidaq::rt;

TEST(RtProfile, ParsesAllKeys) {
  // REQ: SRS-RT-001
  const auto p = rt::parse_profile(R"(
# real-time profile for the bench PC
lock_memory = true
prefault_stack_kib = 256
source.cpu = 1
source.policy = fifo
source.priority = 80
write.cpu = 3     # the disk writer gets its own core
)");
  ASSERT_TRUE(p) << p.error().message;
  EXPECT_TRUE(p->lock_memory);
  EXPECT_EQ(p->prefault_stack_bytes, 256U * 1024U);
  EXPECT_EQ(p->stages[0].cpu, 1);
  EXPECT_EQ(p->stages[0].policy, rt::SchedPolicy::fifo);
  EXPECT_EQ(p->stages[0].priority, 80);
  EXPECT_EQ(p->stages[4].cpu, 3);
  EXPECT_EQ(p->stages[1].cpu, -1);
}

TEST(RtProfile, RejectsBadInputWithLineNumbers) {
  auto e = rt::parse_profile("lock_memory = yes\n");
  ASSERT_FALSE(e);
  EXPECT_EQ(e.error().line, 1);
  e = rt::parse_profile("\n\nsorter.cpu = 2\n");
  ASSERT_FALSE(e);
  EXPECT_EQ(e.error().line, 3);
  EXPECT_FALSE(rt::parse_profile("pair.priority = 120\n"));
  EXPECT_FALSE(rt::parse_profile("decode.policy = fast\n"));
  EXPECT_FALSE(rt::parse_profile("decode.policy = fifo\n")) << "fifo without a priority";
  EXPECT_FALSE(rt::parse_profile("no equals sign\n"));
}

TEST(RtProfile, FormatRoundTrips) {
  rt::RtProfile p;
  p.lock_memory = true;
  p.prefault_stack_bytes = 128 * 1024;
  p.stages[2] = {2, rt::SchedPolicy::rr, 10};
  const auto q = rt::parse_profile(rt::format_profile(p));
  ASSERT_TRUE(q);
  EXPECT_EQ(rt::format_profile(*q), rt::format_profile(p));
}

TEST(Realtime, PinToCpuZero) {
  // REQ: SRS-RT-002
  std::jthread t([] {
    const auto r = rt::pin_current_thread(0);
    ASSERT_TRUE(r) << r.error().message();
    EXPECT_EQ(rt::current_cpu(), 0);
  });
}

TEST(Realtime, InvalidCpuIsAnError) {
  EXPECT_FALSE(rt::pin_current_thread(-1));
  EXPECT_FALSE(rt::pin_current_thread(1 << 20));
}

TEST(Realtime, SchedOtherAlwaysWorksFifoReportsErrors) {
  std::jthread t([] {
    EXPECT_TRUE(rt::set_current_thread_scheduler(rt::SchedPolicy::other, 0));
    EXPECT_FALSE(rt::set_current_thread_scheduler(rt::SchedPolicy::fifo, 0)) << "priority 0 is invalid for fifo";
    // fifo with a valid priority may fail without CAP_SYS_NICE; it must report, not crash.
    const auto r = rt::set_current_thread_scheduler(rt::SchedPolicy::fifo, 10);
    if (!r) {
      RecordProperty("fifo_error", r.error().message());
    }
  });
}

TEST(Realtime, ApplyStageReportsWhatHappened) {
  std::jthread t([] {
    const auto st = rt::apply_stage({0, rt::SchedPolicy::other, 0}, 128 * 1024);
    EXPECT_TRUE(st.applied);
    EXPECT_TRUE(st.pinned);
    EXPECT_TRUE(st.scheduled);
    EXPECT_EQ(st.running_cpu, 0);
    EXPECT_FALSE(st.error);
  });
}

TEST(Realtime, PrefaultedStackDoesNotFaultAgain) {
  // REQ: SRS-RT-003
  std::jthread t([] {
    rt::prefault_stack(512 * 1024);
    const auto before = rt::thread_page_faults();
    rt::prefault_stack(512 * 1024);  // same pages again: already mapped
    const auto after = rt::thread_page_faults();
    EXPECT_LE(after.minor - before.minor, 2) << "pages should already be resident";
  });
}

TEST(Realtime, TimerSlackCanBeSet) {
  std::jthread t([] { EXPECT_TRUE(rt::set_timer_slack_ns(1)); });
}
