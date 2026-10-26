// SPDX-License-Identifier: MIT
// Heartbeats, the health they make up, and the link to the service manager that reports it
// (Chapter 25). The manager's side is a datagram socket the test binds, so the test reads
// exactly what systemd would receive.
#include <gtest/gtest.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "eventually.hpp"
#include "minidaq/control/service_manager.hpp"
#include "minidaq/hw/fake_board.hpp"
#include "minidaq/hw/slow_control.hpp"
#include "minidaq/rt/health.hpp"

using namespace minidaq;
using namespace std::chrono_literals;
using test_support::eventually;

namespace {

using Clock = rt::Heartbeat::Clock;

// The service manager's end: an abstract unix datagram socket, unique to this process.
class FakeManager {
 public:
  FakeManager()
      : name_{"@minidaq-test-notify-" + std::to_string(::getpid()) + "-" +
              std::to_string(next_++)} {
    fd_ = ::socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    std::memcpy(addr.sun_path, name_.data(), name_.size());
    addr.sun_path[0] = '\0';
    const auto len = static_cast<socklen_t>(offsetof(sockaddr_un, sun_path) + name_.size());
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the sockets API's sockaddr
    bound_ = ::bind(fd_, reinterpret_cast<const sockaddr*>(&addr), len) == 0;
  }
  ~FakeManager() { ::close(fd_); }
  FakeManager(const FakeManager&) = delete;
  FakeManager& operator=(const FakeManager&) = delete;
  FakeManager(FakeManager&&) = delete;
  FakeManager& operator=(FakeManager&&) = delete;

  [[nodiscard]] const std::string& name() const { return name_; }
  [[nodiscard]] bool bound() const { return bound_; }
  // Every message received so far, in order.
  std::vector<std::string> received() {
    std::array<char, 4096> buf{};
    for (;;) {
      const auto n = ::recv(fd_, buf.data(), buf.size(), 0);
      if (n <= 0) {
        break;
      }
      messages_.emplace_back(buf.data(), static_cast<std::size_t>(n));
    }
    return messages_;
  }
  std::size_t count(const std::string& message) {
    const auto all = received();
    return static_cast<std::size_t>(std::count(all.begin(), all.end(), message));
  }

 private:
  static inline int next_ = 0;
  std::string name_;
  int fd_ = -1;
  bool bound_ = false;
  std::vector<std::string> messages_;
};

TEST(Health, ALoopIsHealthyWhileItBeatsAndGetsItsLimitToStart) {
  // REQ: SRS-PLT-002
  const auto t0 = Clock::now();
  auto beat = std::make_shared<rt::Heartbeat>();
  rt::HealthMonitor health;
  health.watch("loop", beat, 1000ms, t0);
  EXPECT_TRUE(health.silent(t0 + 999ms).empty()) << "a loop that has not started yet has its limit";
  const auto never = health.silent(t0 + 1001ms);
  ASSERT_EQ(never.size(), 1U);
  EXPECT_TRUE(never[0].never_beat);
  EXPECT_EQ(rt::describe(never), "loop never beat");

  beat->beat_at(t0 + 1500ms);
  EXPECT_TRUE(health.silent(t0 + 2500ms).empty());
  const auto stopped = health.silent(t0 + 3900ms);
  ASSERT_EQ(stopped.size(), 1U);
  EXPECT_FALSE(stopped[0].never_beat);
  EXPECT_EQ(stopped[0].silent_for, 2400ms);
  EXPECT_EQ(rt::describe(stopped), "loop silent for 2.4 s");
}

TEST(Health, EveryLoopCountsAndABeatFromBeforeTheWatchDoesNotUseUpTheLimit) {
  // REQ: SRS-PLT-002
  const auto t0 = Clock::now();
  auto a = std::make_shared<rt::Heartbeat>();
  auto b = std::make_shared<rt::Heartbeat>();
  a->beat_at(t0 - 1h);
  rt::HealthMonitor health;
  health.watch("a", a, 100ms, t0);
  health.watch("b", b, 200ms, t0);
  EXPECT_TRUE(health.silent(t0 + 100ms).empty());
  b->beat_at(t0 + 150ms);
  const auto s = health.silent(t0 + 300ms);
  ASSERT_EQ(s.size(), 1U);
  EXPECT_EQ(s[0].name, "a");
  EXPECT_EQ(rt::describe(health.silent(t0 + 400ms)), "a silent for 0.4 s; b silent for 0.2 s");
}

TEST(Health, TheSlowControlBeatsOncePerCycleAndAHungBusStopsIt) {
  // REQ: SRS-PLT-002
  std::int64_t now = 0;
  hw::FakeBoard board{1, [&now] { return now; }};
  hw::SlowControl sc{{}, {&board}};
  const auto beat = sc.heartbeat();
  EXPECT_FALSE(beat->last().has_value());
  sc.step(now);
  ASSERT_TRUE(beat->last().has_value());

  // A cycle on its own thread, against a bus that hangs: the heartbeat stays where it was.
  sc.start([&now] { return now; });
  ASSERT_TRUE(eventually([&] { return sc.cycles() >= 3; }));
  board.set_fault(hw::BoardFault::hung_bus);
  rt::HealthMonitor health;
  health.watch("slow control", beat, 300ms);
  ASSERT_TRUE(eventually([&] { return !health.silent().empty(); }))
      << "a cycle stuck in a register read is a silent loop";
  const auto cycles = sc.cycles();
  EXPECT_FALSE(eventually([&] { return sc.cycles() > cycles; }, 200ms)) << "and it stays stuck";

  board.set_fault(hw::BoardFault::none);  // the read returns (as a timeout) and the cycles resume
  ASSERT_TRUE(eventually([&] { return health.silent().empty(); }));
  sc.stop();
}

TEST(ServiceManager, WithoutANotifySocketEveryCallDoesNothing) {
  // REQ: SRS-PLT-001
  ::unsetenv("NOTIFY_SOCKET");  // NOLINT(concurrency-mt-unsafe): the test's own environment
  ::unsetenv("WATCHDOG_USEC");  // NOLINT(concurrency-mt-unsafe)
  ::unsetenv("WATCHDOG_PID");   // NOLINT(concurrency-mt-unsafe)
  auto link = control::ServiceManagerLink::from_environment();
  ASSERT_TRUE(link.has_value());
  EXPECT_FALSE(link->enabled());
  EXPECT_FALSE(link->watchdog_interval().has_value());
  EXPECT_EQ(link->ready("idle"), 0);
  rt::HealthMonitor health;
  const control::Watchdog watchdog{*link, health, {}};
  EXPECT_FALSE(watchdog.running());
}

TEST(ServiceManager, ReadsTheEnvironmentAsSdNotifyDoes) {
  // REQ: SRS-PLT-001, SRS-PLT-002
  ::setenv("NOTIFY_SOCKET", "@abc", 1);                             // NOLINT(concurrency-mt-unsafe)
  ::setenv("WATCHDOG_USEC", "4000000", 1);                          // NOLINT(concurrency-mt-unsafe)
  ::setenv("WATCHDOG_PID", std::to_string(::getpid()).c_str(), 1);  // NOLINT(concurrency-mt-unsafe)
  auto link = control::ServiceManagerLink::from_environment();
  ASSERT_TRUE(link.has_value());
  EXPECT_EQ(link->socket(), "@abc");
  EXPECT_EQ(link->watchdog_interval(), std::chrono::microseconds{4'000'000});

  // Variables meant for another process: no watchdog here.
  ::setenv("WATCHDOG_PID", std::to_string(::getpid() + 1).c_str(),
           1);  // NOLINT(concurrency-mt-unsafe)
  link = control::ServiceManagerLink::from_environment();
  ASSERT_TRUE(link.has_value());
  EXPECT_FALSE(link->watchdog_interval().has_value());

  ::setenv("WATCHDOG_USEC", "soon", 1);  // NOLINT(concurrency-mt-unsafe)
  EXPECT_FALSE(control::ServiceManagerLink::from_environment().has_value());
  ::setenv("WATCHDOG_USEC", "4000000", 1);      // NOLINT(concurrency-mt-unsafe)
  ::setenv("NOTIFY_SOCKET", "vsock:2:999", 1);  // NOLINT(concurrency-mt-unsafe)
  EXPECT_FALSE(control::ServiceManagerLink::from_environment().has_value());
  ::unsetenv("NOTIFY_SOCKET");  // NOLINT(concurrency-mt-unsafe)
  ::unsetenv("WATCHDOG_USEC");  // NOLINT(concurrency-mt-unsafe)
  ::unsetenv("WATCHDOG_PID");   // NOLINT(concurrency-mt-unsafe)
}

TEST(ServiceManager, SendsReadyStatusAndStoppingAsOneDatagramEach) {
  // REQ: SRS-PLT-001
  FakeManager manager;
  ASSERT_TRUE(manager.bound());
  auto link = control::ServiceManagerLink::to(manager.name(), std::nullopt);
  ASSERT_TRUE(link.has_value());
  EXPECT_EQ(link->ready("state idle"), 0);
  EXPECT_EQ(link->stopping("signal 15"), 0);
  ASSERT_TRUE(eventually([&] { return manager.received().size() == 2; }));
  EXPECT_EQ(manager.received()[0], "READY=1\nSTATUS=state idle");
  EXPECT_EQ(manager.received()[1], "STOPPING=1\nSTATUS=signal 15");

  // A manager that has gone: the error is reported, never thrown.
  auto gone = control::ServiceManagerLink::to("@minidaq-test-nobody-listens", std::nullopt);
  ASSERT_TRUE(gone.has_value());
  EXPECT_NE(gone->ready("x"), 0);
}

TEST(ServiceManager, TheWatchdogPingsOnlyWhileEveryLoopBeats) {
  // REQ: SRS-PLT-002
  FakeManager manager;
  ASSERT_TRUE(manager.bound());
  auto link = control::ServiceManagerLink::to(manager.name(), std::chrono::microseconds{40'000});
  ASSERT_TRUE(link.has_value());
  auto beat = std::make_shared<rt::Heartbeat>();
  beat->beat();
  rt::HealthMonitor health;
  health.watch("loop", beat, 200ms);
  std::vector<std::pair<bool, std::string>> changes;
  std::mutex mu;
  const control::Watchdog watchdog{*link, health, [&](bool healthy, const std::string& why) {
                                     const std::lock_guard lock{mu};
                                     changes.emplace_back(healthy, why);
                                   }};
  ASSERT_TRUE(watchdog.running());
  EXPECT_EQ(watchdog.period(), std::chrono::microseconds{20'000}) << "half the interval";

  // Healthy: pings arrive.
  ASSERT_TRUE(eventually([&] {
    beat->beat();
    return manager.count("WATCHDOG=1") >= 5;
  }));
  // The loop stops: the pings stop, the manager is told why, and so is the audit trail.
  ASSERT_TRUE(eventually([&] {
    const auto all = manager.received();
    return !all.empty() && all.back().rfind("STATUS=unhealthy: loop silent for", 0) == 0;
  }));
  const auto pings = manager.count("WATCHDOG=1");
  {
    const std::lock_guard lock{mu};
    ASSERT_EQ(changes.size(), 1U);
    EXPECT_FALSE(changes[0].first);
    EXPECT_NE(changes[0].second.find("loop silent for"), std::string::npos);
  }
  // Whatever the time it is given, no ping while the loop is silent.
  EXPECT_FALSE(eventually([&] { return manager.count("WATCHDOG=1") > pings; }, 200ms));

  // It beats again: pings resume, and the change is reported.
  ASSERT_TRUE(eventually([&] {
    beat->beat();
    return manager.count("WATCHDOG=1") > pings && manager.count("STATUS=healthy") == 1;
  }));
  const std::lock_guard lock{mu};
  ASSERT_EQ(changes.size(), 2U);
  EXPECT_TRUE(changes[1].first);
}

}  // namespace
