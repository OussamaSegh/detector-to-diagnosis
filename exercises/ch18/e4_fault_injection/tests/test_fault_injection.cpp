// SPDX-License-Identifier: MIT
// Exercise 18.4: acceptance tests of the fault-injecting detector. The inner
// port is a fake that serves a fixed list of words and counts its reads; the
// last two tests put the decorator in front of the real simulated detector and
// run the real acquisition service.
#include <gtest/gtest.h>

#include <chrono>
#include <cstdint>
#include <memory>
#include <numeric>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include <nlohmann/json.hpp>

#include "fault_injection.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"

namespace {

using minidaq::control::DetectorCounter;
using minidaq::control::DetectorPort;
using namespace std::chrono_literals;

// A fake detector: words 1, 2, 3, ... up to `total`, then nothing.
struct FakeState {
  std::uint64_t total = 0;
  std::uint64_t next = 1;
  int reads = 0;
  std::optional<std::string> fault;
};

class Fake final : public DetectorPort {
 public:
  explicit Fake(FakeState& s) : s_{s} {}
  std::size_t read(std::span<std::uint64_t> out) override {
    ++s_.reads;
    std::size_t n = 0;
    while (n < out.size() && s_.next <= s_.total) {
      out[n++] = s_.next++;
    }
    return n;
  }
  [[nodiscard]] std::optional<std::string> fault() const override { return s_.fault; }
  [[nodiscard]] std::string describe() const override { return "fake"; }
  [[nodiscard]] std::vector<DetectorCounter> counters() const override { return {{"packets_lost", 7}}; }

 private:
  FakeState& s_;
};

std::vector<std::uint64_t> read_all(DetectorPort& d, std::size_t chunk = 4, int reads = 50) {
  std::vector<std::uint64_t> got;
  std::vector<std::uint64_t> buf(chunk);
  for (int i = 0; i < reads; ++i) {
    const auto n = d.read(buf);
    got.insert(got.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(n));
  }
  return got;
}

std::vector<std::uint64_t> iota(std::uint64_t from, std::uint64_t to) {
  std::vector<std::uint64_t> v(to - from + 1);
  std::iota(v.begin(), v.end(), from);
  return v;
}

TEST(FaultInjection, WithoutAPlanItIsTransparent) {
  FakeState s;
  s.total = 10;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {}};
  EXPECT_EQ(read_all(d), iota(1, 10));
  EXPECT_FALSE(d.fault().has_value());
}

TEST(FaultInjection, DescribesItselfAndTheInnerPort) {
  FakeState s;
  const ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {}};
  EXPECT_EQ(d.describe(), "fault-injecting(fake)");
}

TEST(FaultInjection, FaultsAfterExactlyTheGivenNumberOfWords) {
  FakeState s;
  s.total = 100;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.fault_after_words = 10, .message = "link down"}};
  EXPECT_EQ(read_all(d, 4), iota(1, 10)) << "reads of 4 words: the third may deliver only 2";
  EXPECT_EQ(d.fault(), "link down");
  EXPECT_EQ(d.delivered(), 10U);
}

TEST(FaultInjection, AfterTheFaultTheInnerPortIsNotRead) {
  FakeState s;
  s.total = 100;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.fault_after_words = 5}};
  (void)read_all(d, 8, 1);
  ASSERT_TRUE(d.fault().has_value());
  const int reads = s.reads;
  (void)read_all(d, 8, 10);
  EXPECT_EQ(s.reads, reads) << "a faulted device delivers nothing, and is not asked for more";
}

TEST(FaultInjection, ARealFaultIsNeverHidden) {
  FakeState s;
  s.total = 100;
  s.fault = "inner overflow";
  const ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.fault_after_words = 50}};
  EXPECT_EQ(d.fault(), "inner overflow");
}

TEST(FaultInjection, DropsEveryNthWordAndCountsIt) {
  FakeState s;
  s.total = 10;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.drop_every = 3}};
  EXPECT_EQ(read_all(d, 4), (std::vector<std::uint64_t>{1, 2, 4, 5, 7, 8, 10}));
  const auto c = d.counters();
  ASSERT_EQ(c.size(), 2U);
  EXPECT_EQ(c[0].name, "packets_lost") << "the inner port's counters come first, unchanged";
  EXPECT_EQ(c[0].value, 7U);
  EXPECT_EQ(c[1].name, "rejected_injected");
  EXPECT_EQ(c[1].value, 3U);
}

TEST(FaultInjection, DropsCountAcrossReads) {
  FakeState s;
  s.total = 9;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.drop_every = 2}};
  EXPECT_EQ(read_all(d, 1), (std::vector<std::uint64_t>{1, 3, 5, 7, 9})) << "one word per read";
}

TEST(FaultInjection, AStallReturnsNothingAndConsumesNothing) {
  FakeState s;
  s.total = 6;
  ex::FaultInjectingDetector d{std::make_unique<Fake>(s), {.stall_from = 1, .stall_reads = 3}};
  std::vector<std::uint64_t> buf(2);
  EXPECT_EQ(d.read(buf), 2U);
  for (int i = 0; i < 3; ++i) {
    EXPECT_EQ(d.read(buf), 0U) << "stalled read " << i;
  }
  EXPECT_EQ(s.reads, 1) << "a stall does not read the inner port";
  EXPECT_EQ(read_all(d, 2, 5), iota(3, 6)) << "after the stall the stream continues where it was";
}

// --- With the real service

minidaq::control::ServiceOptions options_with(ex::FaultPlan plan) {
  auto o = minidaq::control::with_default_adapters();
  o.detector = [base = o.detector, plan](const minidaq::config::AcquisitionConfig& cfg,
                                         std::string& error) -> std::unique_ptr<DetectorPort> {
    auto inner = base(cfg, error);
    if (!inner) {
      return nullptr;
    }
    return std::make_unique<ex::FaultInjectingDetector>(std::move(inner), plan);
  };
  o.monitor_period = 5ms;
  return o;
}

TEST(FaultInjection, TheServiceEndsTheRunInAFault) {
  minidaq::control::AcquisitionService svc{options_with({.fault_after_words = 200'000, .message = "link down"})};
  ASSERT_TRUE(svc.configure({}, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(minidaq::control::AcqState::fault, 10s)) << to_string(svc.state());
  const auto st = svc.status();
  EXPECT_EQ(st["fault"], "detector: link down");
  EXPECT_EQ(st["integrity"]["complete"], false);
}

TEST(FaultInjection, DroppedWordsMakeTheRunIncomplete) {
  minidaq::control::AcquisitionService svc{options_with({.drop_every = 1'000})};
  ASSERT_TRUE(svc.configure({}, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  // Wait until some words have been dropped, then end the run normally.
  const auto deadline = std::chrono::steady_clock::now() + 10s;
  const auto dropped = [&svc] {
    const auto st = svc.status();
    const auto it = st.find("detector_counters");
    return it != st.end() && it->contains("rejected_injected") && (*it)["rejected_injected"] != 0;
  };
  while (!dropped() && std::chrono::steady_clock::now() < deadline) {
    std::this_thread::sleep_for(1ms);  // sleep: poll the status until a word was dropped
  }
  ASSERT_TRUE(svc.stop("test").ok);
  ASSERT_TRUE(svc.wait_for(minidaq::control::AcqState::configured, 10s));
  const auto st = svc.status();
  EXPECT_EQ(st["integrity"]["complete"], false) << "a word the device dropped is a loss, not a silent change";
}

}  // namespace
