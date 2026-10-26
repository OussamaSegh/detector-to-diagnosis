// SPDX-License-Identifier: MIT
// The hardware description, its adapter and the acquisition service together (Chapter 22): the
// simulated boards of a description, a slow control that runs on its own thread, and a service
// that will not start a run on boards that are not ready and stops one on a hardware fault.
#include <gtest/gtest.h>
#include <unistd.h>

#include <chrono>
#include <fstream>
#include <mutex>
#include <nlohmann/json.hpp>
#include <string>

#include "eventually.hpp"
#include "minidaq/config/hardware_config.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/hardware.hpp"
#include "traced.hpp"

using namespace minidaq;
using namespace minidaq::control;
using namespace std::chrono_literals;
using nlohmann::json;

namespace {

// A file whose content is the temperature of a simulated board.
class TemperatureFile {
 public:
  TemperatureFile()
      : path_{::testing::TempDir() + "temperature-" + std::to_string(::getpid()) + ".txt"} {
    set(25.0);
  }
  ~TemperatureFile() { (void)std::remove(path_.c_str()); }
  TemperatureFile(const TemperatureFile&) = delete;
  TemperatureFile& operator=(const TemperatureFile&) = delete;
  TemperatureFile(TemperatureFile&&) = delete;
  TemperatureFile& operator=(TemperatureFile&&) = delete;
  void set(double c) const { std::ofstream{path_} << c << '\n'; }
  [[nodiscard]] const std::string& path() const { return path_; }

 private:
  std::string path_;
};

// Two simulated boards that ramp to their bias in about half a second.
config::HardwareConfig two_boards(const std::string& temperature_file,
                                  double ramp_v_per_s = 100.0) {
  json doc{{"schema_version", "1.0"},
           {"backend", "simulated"},
           {"period_ms", 10},
           {"bias", {{"ramp_v_per_s", ramp_v_per_s}}},
           {"boards", {{{"slot", 3}, {"temperature_file", temperature_file}}, {{"slot", 4}}}}};
  auto cfg = config::parse_hardware_config(doc.dump());
  EXPECT_TRUE(cfg) << config::format_errors(cfg.error());
  return *cfg;
}

std::shared_ptr<HardwarePort> open(const config::HardwareConfig& cfg) {
  auto h = SlowControlHardware::open(cfg);
  EXPECT_TRUE(h) << h.error();
  return std::shared_ptr<HardwarePort>(std::move(*h));
}

// A sink that keeps the run record it is given at the end of the run.
struct Records {
  std::mutex mu;
  std::string last;
};
class RecordingSink final : public CoincidenceSinkPort {
 public:
  explicit RecordingSink(Records& r) : records_{r} {}
  void write(std::span<const Coincidence>) override {}
  std::optional<std::string> close(std::string_view record) override {
    const std::lock_guard lock{records_.mu};
    records_.last = record;
    return std::nullopt;
  }
  [[nodiscard]] std::string describe() const override { return "recording"; }

 private:
  Records& records_;
};

ServiceOptions options(std::shared_ptr<HardwarePort> hw, Records* records = nullptr) {
  ServiceOptions o = with_default_adapters();
  o.hardware = std::move(hw);
  o.monitor_period = 5ms;
  if (records != nullptr) {
    o.sink = [records](const config::AcquisitionConfig&, std::string&) {
      return std::make_unique<RecordingSink>(*records);
    };
  }
  return o;
}

config::AcquisitionConfig small() {
  config::AcquisitionConfig c;
  c.source.rate_hz = 1e6;
  c.pipeline.batch_size = 512;
  c.pipeline.batches_per_channel = 8;
  return c;
}

}  // namespace

TEST(HardwareConfig, ReadsTheSettingsInTheirUnitsAndKeepsTheDefaults) {
  // REQ: SRS-HW-010
  auto c = config::parse_hardware_config(R"({
    "schema_version": "1.0", // a comment, as in the acquisition configuration
    "boards": [{"slot": 2, "temperature_c": 30.5, "fault": "weak_supply"}],
    "bias": {"breakdown_25c_v": 24.2, "breakdown_mv_per_c": 21.5, "overvoltage_v": 6.0,
             "min_v": 20.0, "max_v": 33.0, "ramp_v_per_s": 2.5},
    "temperature": {"alarm_c": 45.0}
  })");
  ASSERT_TRUE(c) << config::format_errors(c.error());
  EXPECT_EQ(c->backend, "simulated");
  ASSERT_EQ(c->boards.size(), 1U);
  EXPECT_EQ(c->boards[0].slot, 2U);
  EXPECT_EQ(c->boards[0].fault, "weak_supply");
  EXPECT_DOUBLE_EQ(c->settings.law.vbd_25c_mv, 24'200.0);
  EXPECT_DOUBLE_EQ(c->settings.law.overvoltage_mv, 6'000.0);
  EXPECT_DOUBLE_EQ(c->settings.law.bias_mv(25.0), 30'200.0);
  EXPECT_EQ(c->settings.ramp_mv_per_s, 2'500U);
  EXPECT_DOUBLE_EQ(c->settings.temp_alarm_c, 45.0);
  EXPECT_DOUBLE_EQ(c->settings.temp_warning_c, 35.0) << "a default";
  EXPECT_EQ(c->settings.period, 100ms);
}

TEST(HardwareConfig, ReportsEveryProblemWithItsLocation) {
  // REQ: SRS-HW-010
  auto c = config::parse_hardware_config(R"({
    "schema_version": "1.1", "backend": "mmio", "period_ms": 1,
    "boards": [{"device": "/dev/uio0", "slot": 1}, {"offset": 0}],
    "bias": {"min_v": 44.0},
    "temperature": {"warning_c": 41.0},
    "boards_extra": true
  })");
  ASSERT_FALSE(c);
  const std::string errors = config::format_errors(c.error());
  for (const char* expected :
       {"/schema_version: must be \"1.0\"", "/period_ms: must be between 10 and 10000",
        "/boards/0/slot: unknown key", "/boards/1/device: is required",
        "/bias/min_v: must be below /bias/max_v",
        "/temperature: must have min_c < warning_c < alarm_c", "/boards_extra: unknown key"}) {
    EXPECT_NE(errors.find(expected), std::string::npos) << expected << "\nin:\n" << errors;
  }
  EXPECT_FALSE(config::parse_hardware_config(
      R"({"schema_version": "1.0", "boards": [{"slot": 1}, {"slot": 1}]})"));
  EXPECT_FALSE(config::parse_hardware_config(R"({"schema_version": "1.0"})"))
      << "boards are required";
  EXPECT_FALSE(config::parse_hardware_config("not json"));
}

TEST(HardwareService, DoesNotStartARunWhileABoardIsNotReady) {
  // REQ: SRS-HW-006
  const TemperatureFile file;
  AcquisitionService svc{options(open(two_boards(file.path(), 0.5)))};  // 80 s of ramp
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  const auto r = svc.start("test");
  EXPECT_FALSE(r.ok);
  EXPECT_EQ(r.code, "device_error");
  EXPECT_TRUE(r.message.starts_with("hardware not ready: ")) << r.message;
  EXPECT_EQ(svc.state(), AcqState::configured) << "the configuration is kept";
}

TEST(HardwareService, AHardwareFaultStopsTheRunAndAResetAcknowledgesIt) {
  // REQ: SRS-HW-006, SRS-HW-005
  const std::uint64_t began = test_support::trace_clock_ns();
  const TemperatureFile file;
  AcquisitionService svc{options(open(two_boards(file.path())))};
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(
      test_support::eventually([&] { return svc.status()["hardware"]["ready"].get<bool>(); }));
  ASSERT_TRUE(svc.start("test").ok);

  file.set(41.0);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, test_support::patience));
  const auto st = svc.status();
  EXPECT_EQ(st["fault"],
            "hw: board 0 (slot 3): temperature 41.00 C is at or above the alarm limit 40.0 C");
  EXPECT_EQ(st["hardware"]["boards"][0]["state"], "fault");
  EXPECT_EQ(st["hardware"]["boards"][1]["state"], "ready") << "only the hot board is switched off";
  EXPECT_FALSE(st["integrity"]["complete"].get<bool>());
  const auto faults = test_support::traced_since(began, TraceCode::fault);
  ASSERT_EQ(faults.size(), 1U);
  EXPECT_EQ(faults[0].b, static_cast<std::uint64_t>(FaultSource::hardware));

  // Still hot: the acknowledgment of the reset does not hold, and the fault comes back.
  ASSERT_TRUE(svc.reset("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, test_support::patience));
  file.set(25.0);
  ASSERT_TRUE(test_support::eventually(
      [&] { return svc.status()["hardware"]["boards"][0]["temperature_c"] == 25.0; }));
  ASSERT_TRUE(svc.reset("test").ok);
  EXPECT_EQ(svc.state(), AcqState::idle);
  ASSERT_TRUE(svc.configure(small(), "test").ok);
  ASSERT_TRUE(test_support::eventually([&] { return svc.start("test").ok; }))
      << "after the board has ramped again";
  ASSERT_TRUE(svc.stop("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
}

TEST(HardwareService, AFaultWhileIdleIsReportedAtOnce) {
  // REQ: SRS-HW-006
  const TemperatureFile file;
  file.set(3.0);
  AcquisitionService svc{options(open(two_boards(file.path())))};
  ASSERT_TRUE(svc.wait_for(AcqState::fault, test_support::patience));
  EXPECT_EQ(svc.status()["fault"],
            "hw: board 0 (slot 3): temperature 3.00 C is below 5.0 C: the sensor is not believed");
}

TEST(HardwareService, StatusAndRunRecordShowEachBoard) {
  // REQ: SRS-HW-007
  const TemperatureFile file;
  file.set(30.0);
  Records records;
  AcquisitionService svc{options(open(two_boards(file.path())), &records)};
  EXPECT_TRUE(AcquisitionService{with_default_adapters()}.status()["hardware"].is_null())
      << "a service without hardware says so";
  auto c = small();
  c.stop_after_s = 0.01;
  ASSERT_TRUE(svc.configure(c, "test").ok);
  ASSERT_TRUE(test_support::eventually([&] { return svc.start("test").ok; }));
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
  const std::lock_guard lock{records.mu};
  const json record = json::parse(records.last);
  const json& hw = record["hardware"];
  EXPECT_EQ(hw["describe"], "2 boards, simulated");
  EXPECT_EQ(hw["ready"], true);
  ASSERT_EQ(hw["boards"].size(), 2U);
  const json& b = hw["boards"][0];
  EXPECT_EQ(b["slot"], 3);
  EXPECT_EQ(b["state"], "ready");
  EXPECT_EQ(b["temperature"], "normal");
  EXPECT_DOUBLE_EQ(b["temperature_c"].get<double>(), 30.0);
  EXPECT_DOUBLE_EQ(b["target_v"].get<double>(), 40.87);
  EXPECT_DOUBLE_EQ(b["setpoint_v"].get<double>(), 40.87);
  EXPECT_NEAR(b["monitor_v"].get<double>(), 40.87, 0.05);
  EXPECT_TRUE(b["fault"].is_null());
  EXPECT_DOUBLE_EQ(hw["boards"][1]["setpoint_v"].get<double>(), 40.7) << "board 4 is at 25 C";
}
