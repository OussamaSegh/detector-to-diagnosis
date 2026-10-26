// SPDX-License-Identifier: MIT
// How the acquisition service talks to its sink (Chapter 18): interaction
// tests with GoogleMock. The other service tests check states and counters;
// these check the order of the calls, which no state shows: every write()
// comes before the one close() that makes the run durable.
#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <chrono>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "eventually.hpp"

using namespace minidaq;
using namespace minidaq::control;
using namespace std::chrono_literals;
using ::testing::_;
using ::testing::AnyNumber;
using ::testing::HasSubstr;
using ::testing::InSequence;
using ::testing::NiceMock;
using ::testing::Return;

namespace {

// [snippet:mock]
class MockSink : public CoincidenceSinkPort {
 public:
  MOCK_METHOD(void, write, (std::span<const Coincidence> batch), (override));
  MOCK_METHOD(std::optional<std::string>, close, (std::string_view run_record), (override));
  MOCK_METHOD(std::string, describe, (), (const, override));
};
// [/snippet:mock]

// The service makes its sink through a factory; the test keeps a pointer to
// the mock to set expectations before the service uses it.
ServiceOptions with_sink(std::unique_ptr<CoincidenceSinkPort>& next) {
  ServiceOptions o = with_default_adapters();
  o.sink = [&next](const config::AcquisitionConfig&, std::string&) { return std::move(next); };
  o.monitor_period = 5ms;
  return o;
}

config::AcquisitionConfig short_run() {
  config::AcquisitionConfig c;
  c.stop_after_s = 0.05;  // the service ends the run by itself
  return c;
}

// [snippet:sequence]
TEST(ServiceInteractions, ARunClosesTheSinkOnceAfterTheLastWrite) {
  // REQ: SRS-CTL-035
  auto sink = std::make_unique<NiceMock<MockSink>>();
  {
    InSequence order;  // a write() after close() would fail the test
    EXPECT_CALL(*sink, write(_)).Times(AnyNumber());
    EXPECT_CALL(*sink, close(HasSubstr("\"integrity\""))).WillOnce(Return(std::nullopt));
  }
  std::unique_ptr<CoincidenceSinkPort> next = std::move(sink);
  AcquisitionService svc{with_sink(next)};
  ASSERT_TRUE(svc.configure(short_run(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience)) << to_string(svc.state());
}
// [/snippet:sequence]

TEST(ServiceInteractions, ASinkThatCannotCloseFaultsTheRun) {
  // REQ: SRS-CTL-013, SRS-CTL-035
  auto sink = std::make_unique<NiceMock<MockSink>>();
  EXPECT_CALL(*sink, close(_)).WillOnce(Return(std::optional<std::string>{"disk full"}));
  std::unique_ptr<CoincidenceSinkPort> next = std::move(sink);
  AcquisitionService svc{with_sink(next)};
  ASSERT_TRUE(svc.configure(short_run(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, test_support::patience)) << to_string(svc.state());
  EXPECT_EQ(svc.status()["fault"], "sink: disk full");
}

// After a fault the data is not known to be complete, so the sink is not asked
// to make it durable: its files keep their .part names (Chapter 12).
TEST(ServiceInteractions, AFaultedRunDoesNotCloseTheSink) {
  // REQ: SRS-CTL-035
  auto sink = std::make_unique<NiceMock<MockSink>>();
  EXPECT_CALL(*sink, close(_)).Times(0);
  std::unique_ptr<CoincidenceSinkPort> next = std::move(sink);
  ServiceOptions o = with_sink(next);
  o.detector = [](const config::AcquisitionConfig&, std::string&) -> std::unique_ptr<DetectorPort> {
    struct Failing final : DetectorPort {
      std::size_t read(std::span<std::uint64_t>) override { return 0; }
      [[nodiscard]] std::optional<std::string> fault() const override { return "link down"; }
      [[nodiscard]] std::string describe() const override { return "failing"; }
    };
    return std::make_unique<Failing>();
  };
  AcquisitionService svc{o};
  ASSERT_TRUE(svc.configure(short_run(), "test").ok);
  ASSERT_TRUE(svc.start("test").ok);
  ASSERT_TRUE(svc.wait_for(AcqState::fault, test_support::patience)) << to_string(svc.state());
  ASSERT_TRUE(svc.reset("test").ok);  // destroys the sink, and the mock checks its expectations
}

}  // namespace
