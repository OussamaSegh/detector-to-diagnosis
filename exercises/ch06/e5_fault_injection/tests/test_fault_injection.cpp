// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 6.5: MiniDAQ's fault handling, end to end,
// with injected faults instead of broken hardware.
#include <gtest/gtest.h>

#include <chrono>
#include <memory>

#include <nlohmann/json.hpp>

#include "faulty_detector.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"

using namespace std::chrono_literals;
using minidaq::control::AcqState;
using minidaq::control::AcquisitionService;

namespace {

struct Rig {
  std::shared_ptr<ex::FaultCounts> counts = std::make_shared<ex::FaultCounts>();
  std::unique_ptr<AcquisitionService> service;

  explicit Rig(ex::FaultPlan plan) {
    auto o = minidaq::control::with_default_adapters();
    o.detector = ex::faulty_factory(minidaq::control::make_default_detector, plan, counts);
    o.monitor_period = 5ms;
    service = std::make_unique<AcquisitionService>(o);
  }

  // 200,000 words at 1 M/s (0.2 s), small batches.
  void run() {
    minidaq::config::AcquisitionConfig c;
    c.source.rate_hz = 1e6;
    c.stop_after_s = 0.2;
    c.pipeline.batch_size = 512;
    c.pipeline.batches_per_channel = 16;
    ASSERT_TRUE(service->configure(c, "test").ok);
    ASSERT_TRUE(service->start("test").ok);
  }
};

}  // namespace

TEST(FaultInjection, WithoutFaultsTheRunCompletes) {
  Rig rig{ex::FaultPlan{}};
  rig.run();
  ASSERT_TRUE(rig.service->wait_for(AcqState::configured, 5s));
  const auto st = rig.service->status();
  EXPECT_EQ(st["stages"][0]["out"], 200'000);
  EXPECT_EQ(st["detector"].get<std::string>().rfind("faulty(", 0), 0U);
}

TEST(FaultInjection, LinkDownFaultsTheRun) {
  ex::FaultPlan p;
  p.link_down_after_words = 50'000;
  Rig rig{p};
  rig.run();
  ASSERT_TRUE(rig.service->wait_for(AcqState::fault, 5s)) << to_string(rig.service->state());
  const auto st = rig.service->status();
  EXPECT_EQ(st["fault"], "detector: link down after 50000 words");
  EXPECT_LT(st["stages"][0]["out"].get<std::uint64_t>(), 200'000U);
  EXPECT_FALSE(rig.service->start("test").ok) << "a fault must be reset before the next run";
  EXPECT_TRUE(rig.service->reset("test").ok);
}

TEST(FaultInjection, CorruptWordsAreCountedAndNeverPaired) {
  ex::FaultPlan p;
  p.corrupt_every = 1'000;
  Rig rig{p};
  rig.run();
  ASSERT_TRUE(rig.service->wait_for(AcqState::configured, 5s));
  const auto st = rig.service->status();
  EXPECT_EQ(rig.counts->corrupted.load(), 200U);
  EXPECT_EQ(st["stages"][1]["filtered"], 200) << "decode rejects exactly the corrupted words";
  EXPECT_EQ(st["stages"][1]["out"], 200'000 - 200);
}

TEST(FaultInjection, AStallLosesNothingButShowsInLatency) {
  ex::FaultPlan p;
  p.stall_after_words = 50'000;
  p.stall_for = 60ms;
  Rig rig{p};
  rig.run();
  ASSERT_TRUE(rig.service->wait_for(AcqState::configured, 5s));
  const auto st = rig.service->status();
  EXPECT_EQ(rig.counts->stalls.load(), 1U);
  EXPECT_EQ(st["stages"][0]["out"], 200'000) << "back-pressure: the backlog is delivered late, not lost";
  EXPECT_GE(st["latency_ns"]["end_to_end"]["max"].get<std::int64_t>(), 50'000'000)
      << "latency is measured from when the data was due, so the stall shows";
}

TEST(FaultInjection, OutOfOrderDataFaultsTheRun) {
  ex::FaultPlan p;
  p.reorder_after_words = 50'000;
  p.reorder_delay_words = 10'000;
  Rig rig{p};
  rig.run();
  ASSERT_TRUE(rig.service->wait_for(AcqState::fault, 5s)) << to_string(rig.service->state());
  const auto st = rig.service->status();
  EXPECT_GT(rig.counts->reordered.load(), 0U);
  EXPECT_NE(st["fault"].get<std::string>().find("out of time order"), std::string::npos) << st["fault"];
}
