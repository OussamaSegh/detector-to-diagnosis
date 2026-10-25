// SPDX-License-Identifier: MIT
// The acquisition service with simulated ports: the whole control flow is
// tested without hardware, which is what the ports are for.
#include <gtest/gtest.h>

#include <atomic>
#include <mutex>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/synthetic_source.hpp"

using namespace minidaq;
using namespace minidaq::control;
using namespace std::chrono_literals;

namespace {

// A detector that delivers synthetic words as fast as it is asked, and can be
// told to fail. Shared state lives in a Script the test keeps.
struct Script {
  std::atomic<bool> fail{false};
  std::atomic<std::uint64_t> words{0};
  std::atomic<int> created{0};
};

class ScriptedDetector final : public DetectorPort {
 public:
  explicit ScriptedDetector(Script& s) : script_{s}, gen_{sim::SyntheticConfig{}} { script_.created.fetch_add(1); }
  std::size_t read(std::span<std::uint64_t> out) override {
    const std::size_t n = gen_.generate(out.first(std::min<std::size_t>(out.size(), 1024)));
    script_.words.fetch_add(n);
    return n;
  }
  [[nodiscard]] std::optional<std::string> fault() const override {
    return script_.fail.load() ? std::optional<std::string>{"link down"} : std::nullopt;
  }
  [[nodiscard]] std::string describe() const override { return "scripted"; }

 private:
  Script& script_;
  sim::SyntheticSource gen_;
};

struct Audit {
  std::mutex mu;
  std::vector<AuditRecord> records;
  AuditSink sink() {
    return [this](const AuditRecord& r) {
      const std::lock_guard lock{mu};
      records.push_back(r);
    };
  }
  bool contains(std::string_view action, std::string_view detail_part) {
    const std::lock_guard lock{mu};
    for (const auto& r : records) {
      if (r.action == action && r.detail.find(detail_part) != std::string::npos) {
        return true;
      }
    }
    return false;
  }
};

ServiceOptions options(Script& s, Audit* audit = nullptr) {
  ServiceOptions o = with_default_adapters();
  o.detector = [&s](const config::AcquisitionConfig&, std::string&) { return std::make_unique<ScriptedDetector>(s); };
  if (audit != nullptr) {
    o.audit = audit->sink();
  }
  o.monitor_period = 5ms;
  return o;
}

config::AcquisitionConfig small() {
  config::AcquisitionConfig c;
  c.pipeline.batch_size = 512;
  c.pipeline.batches_per_channel = 8;
  return c;
}

}  // namespace

TEST(AcquisitionService, FullLifecycleWithConservation) {
  // REQ: SRS-CTL-010
  Script script;
  Audit audit;
  AcquisitionService svc{options(script, &audit)};
  EXPECT_EQ(svc.state(), AcqState::idle);
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  EXPECT_EQ(svc.state(), AcqState::running);
  while (script.words.load() < 200'000) {
    std::this_thread::sleep_for(1ms);
  }
  const auto r = svc.stop("test");
  ASSERT_TRUE(r.ok);
  EXPECT_TRUE(r.state == AcqState::stopping || r.state == AcqState::configured);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, 5s)) << to_string(svc.state());

  const auto st = svc.status();
  EXPECT_EQ(st["state"], "configured");
  EXPECT_EQ(st["run_id"], 1);
  const auto& stages = st["stages"];
  ASSERT_EQ(stages.size(), 5U);
  EXPECT_EQ(stages[0]["in"].get<std::uint64_t>(), script.words.load()) << "every word read is counted";
  EXPECT_EQ(stages[1]["in"], stages[0]["out"]);
  EXPECT_EQ(stages[4]["in"], stages[3]["out"]) << "everything paired was written";
  EXPECT_GT(st["latency_ns"]["end_to_end"]["count"].get<std::uint64_t>(), 0U);
  EXPECT_TRUE(audit.contains("transition", "running -> stopping (stop)"));
  EXPECT_TRUE(audit.contains("transition", "stopping -> configured (drained)"));
}

TEST(AcquisitionService, AFiniteRunEndsByItself) {
  Script script;
  AcquisitionService svc{options(script)};
  auto c = small();
  c.source.rate_hz = 1e6;
  c.stop_after_s = 0.05;  // 50,000 words
  ASSERT_TRUE(svc.configure(c, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, 5s));
  EXPECT_EQ(svc.status()["stages"][0]["out"], 50'000);
  // A second run gets fresh ports.
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, 5s));
  EXPECT_EQ(script.created.load(), 2);
  EXPECT_EQ(svc.status()["run_id"], 2);
}

TEST(AcquisitionService, IllegalCommandsChangeNothing) {
  // REQ: SRS-CTL-001
  Script script;
  Audit audit;
  AcquisitionService svc{options(script, &audit)};
  auto r = svc.start("test");
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, "illegal_transition");
  EXPECT_EQ(r.message, "cannot start in state idle");
  EXPECT_EQ(svc.state(), AcqState::idle);
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  EXPECT_EQ(svc.configure(small(), "test").code, "illegal_transition") << "no reconfiguring a running acquisition";
  EXPECT_EQ(svc.reset("test").code, "illegal_transition") << "reset does not abort a run";
  EXPECT_EQ(svc.state(), AcqState::running);
  EXPECT_TRUE(audit.contains("configure", "rejected: cannot configure in state running"));
  ASSERT_TRUE(svc.stop("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, 5s));
  ASSERT_TRUE(svc.reset("test").ok);
  EXPECT_EQ(svc.state(), AcqState::idle);
  EXPECT_TRUE(svc.status()["config"].is_null());
}

TEST(AcquisitionService, DetectorFaultStopsTheRunAndNeedsAReset) {
  // REQ: SRS-CTL-011
  Script script;
  AcquisitionService svc{options(script)};
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  std::this_thread::sleep_for(20ms);
  script.fail = true;
  ASSERT_TRUE(svc.wait_for(AcqState::fault, 5s));
  const auto st = svc.status();
  EXPECT_EQ(st["fault"], "detector: link down");
  EXPECT_EQ(svc.start("test").code, "illegal_transition");
  EXPECT_EQ(svc.configure(small(), "test").code, "illegal_transition");
  script.fail = false;
  ASSERT_TRUE(svc.reset("test").ok);  // waits for the pipeline to drain
  EXPECT_EQ(svc.state(), AcqState::idle);
  EXPECT_TRUE(svc.status()["fault"].is_null());
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok) << "recovered";
}

TEST(AcquisitionService, DeviceErrorAtStartKeepsTheConfiguration) {
  ServiceOptions o = with_default_adapters();
  o.detector = [](const config::AcquisitionConfig&, std::string& err) -> std::unique_ptr<DetectorPort> {
    err = "no detector on /dev/fake0";
    return nullptr;
  };
  AcquisitionService svc{o};
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  const auto r = svc.start("test");
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, "device_error");
  EXPECT_EQ(r.message, "no detector on /dev/fake0");
  EXPECT_EQ(svc.state(), AcqState::configured);
}

TEST(AcquisitionService, MissingRealTimeProfileIsAConfigurationError) {
  Script script;
  AcquisitionService svc{options(script)};
  auto c = small();
  c.rt_profile = "/nonexistent/rt.conf";
  const auto r = svc.configure(c, "test");
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, "config_error");
  EXPECT_EQ(svc.state(), AcqState::idle);
  c.rt_profile = MINIDAQ_SOURCE_DIR "/minidaq/profiles/default.conf";
  EXPECT_TRUE(svc.configure(c, "test").ok);
}

TEST(AcquisitionService, DestructionStopsARunningAcquisition) {
  Script script;
  {
    AcquisitionService svc{options(script)};
    ASSERT_TRUE(svc.configure(small(), "test").ok);
    ASSERT_TRUE(svc.start("test").ok);
    std::this_thread::sleep_for(10ms);
  }  // must not hang
  EXPECT_GT(script.words.load(), 0U);
}

TEST(AcquisitionService, DefaultAdaptersRunAtTheConfiguredRate) {
  AcquisitionService svc{with_default_adapters()};
  auto c = small();
  c.source.rate_hz = 2e6;
  c.stop_after_s = 0.1;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, 5s));
  const auto st = svc.status();
  EXPECT_EQ(st["stages"][0]["out"], 200'000);
  EXPECT_GE(st["run"]["elapsed_s"].get<double>(), 0.09) << "paced at 2 M/s";
  EXPECT_EQ(st["sink"], "counting sink (discards data)");
}

namespace {

// Two full batches, the second older than the first: the sorter sees time go
// backwards across batches, which it cannot repair.
class BackwardsDetector final : public DetectorPort {
 public:
  std::size_t read(std::span<std::uint64_t> out) override {
    if (reads_ >= 2 || out.size() < 512) {
      return 0;
    }
    const std::uint64_t base = reads_ == 0 ? 1'000'000 : 0;
    for (std::size_t i = 0; i < 512; ++i) {
      out[i] = packed::pack(packed::Fields{static_cast<std::uint32_t>(i), 1022, base + 100 * i});
    }
    ++reads_;
    return 512;
  }
  [[nodiscard]] std::string describe() const override { return "backwards"; }

 private:
  int reads_ = 0;
};

}  // namespace

TEST(AcquisitionService, OutOfOrderSinglesAreAFault) {
  // REQ: SRS-CTL-012
  ServiceOptions o = with_default_adapters();
  o.detector = [](const config::AcquisitionConfig&, std::string&) { return std::make_unique<BackwardsDetector>(); };
  o.monitor_period = 5ms;
  AcquisitionService svc{o};
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, 5s)) << to_string(svc.state());
  const auto st = svc.status();
  EXPECT_EQ(st["fault"], "sort: 512 singles arrived out of time order");
  EXPECT_EQ(st["late_singles"], 512);
  ASSERT_TRUE(st.contains("sorter")) << "the sorter's counters are part of the status";
  EXPECT_TRUE(st["sorter"].contains("out_of_order"));
}

TEST(AcquisitionService, StatusReportsTheLastIntervalSeparately) {
  Script script;
  auto o = options(script);
  o.interval_period = 30ms;
  AcquisitionService svc{o};
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  EXPECT_FALSE(svc.status().contains("recent_latency_ns")) << "no complete interval yet";
  std::this_thread::sleep_for(150ms);
  const auto st = svc.status();
  ASSERT_TRUE(st.contains("recent_latency_ns"));
  const auto& recent = st["recent_latency_ns"];
  EXPECT_GE(recent["interval_s"].get<double>(), 0.025);
  EXPECT_LT(recent["interval_s"].get<double>(), 0.2);
  const auto in_interval = recent["decode"]["count"].get<std::uint64_t>();
  EXPECT_GT(in_interval, 0U);
  EXPECT_LT(in_interval, st["latency_ns"]["decode"]["count"].get<std::uint64_t>()) << "a part of the run, not all of it";
  ASSERT_TRUE(svc.stop("test").ok);
}

TEST(AcquisitionService, ASinkThatCannotCloseEndsTheRunInAFault) {
  // REQ: SRS-CTL-013
  // Chapter 12: the data of a run must reach stable storage before the run
  // counts as complete; a failure at the end is a fault, not a clean stop.
  struct FailingClose final : CoincidenceSinkPort {
    void write(std::span<const Coincidence>) override {}
    std::optional<std::string> close() override { return "fsync /data: Input/output error"; }
    [[nodiscard]] std::string describe() const override { return "failing close"; }
  };
  Script script;
  auto o = options(script);
  o.sink = [](const config::AcquisitionConfig&, std::string&) { return std::make_unique<FailingClose>(); };
  AcquisitionService svc{o};
  auto c = small();
  c.source.rate_hz = 1e6;
  c.stop_after_s = 0.01;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, 5s)) << to_string(svc.state());
  EXPECT_EQ(svc.status()["fault"], "sink: fsync /data: Input/output error");
}

TEST(AcquisitionService, WithoutAdaptersStartIsADeviceError) {
  AcquisitionService svc;  // ports only: nothing to read from or write to
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  const auto r = svc.start("test");
  EXPECT_EQ(r.code, "device_error");
  EXPECT_EQ(svc.state(), AcqState::configured);
}

TEST(AcquisitionService, ProfilePathMustBeASmallRegularFile) {
  // The rt_profile path arrives from a control client: untrusted input.
  Script script;
  AcquisitionService svc{options(script)};
  auto c = small();
  for (const char* path : {"/dev/zero", "/tmp", "/nonexistent/rt.conf"}) {
    c.rt_profile = path;
    const auto r = svc.configure(c, "test");
    EXPECT_EQ(r.code, "config_error") << path;
    EXPECT_EQ(svc.state(), AcqState::idle);
  }
  c.rt_profile = "/dev/zero";
  EXPECT_NE(svc.configure(c, "test").message.find("not a regular file"), std::string::npos);
}
