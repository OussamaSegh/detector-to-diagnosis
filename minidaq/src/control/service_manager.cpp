// SPDX-License-Identifier: MIT
#include "minidaq/control/service_manager.hpp"

#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <utility>

#include "minidaq/core/parse_number.hpp"

namespace minidaq::control {

namespace {

const char* env(const char* name) {
  // Read once at start-up, before any thread exists.
  return std::getenv(name);  // NOLINT(concurrency-mt-unsafe)
}

}  // namespace

Expected<ServiceManagerLink, std::string> ServiceManagerLink::to(
    std::string socket, std::optional<std::chrono::microseconds> watchdog) {
  if (!socket.empty() && socket.front() != '/' && socket.front() != '@') {
    // systemd also knows "vsock:" addresses, for virtual machines; MiniDAQ does not need them.
    return Unexpected{"NOTIFY_SOCKET \"" + socket + "\" is not a path or an abstract socket"};
  }
  if (socket.size() >= sizeof(sockaddr_un::sun_path)) {
    return Unexpected{std::string{"NOTIFY_SOCKET is longer than a unix socket address can be"}};
  }
  ServiceManagerLink link;
  link.socket_ = std::move(socket);
  link.watchdog_ = link.socket_.empty() ? std::nullopt : watchdog;
  return link;
}

// [snippet:environment]
Expected<ServiceManagerLink, std::string> ServiceManagerLink::from_environment() {
  const char* notify_socket = env("NOTIFY_SOCKET");
  std::optional<std::chrono::microseconds> watchdog;
  if (const char* usec = env("WATCHDOG_USEC"); usec != nullptr) {
    std::uint64_t us = 0;
    if (!parse_into<std::uint64_t>(usec, us, 1, std::uint64_t{24} * 3600 * 1'000'000)) {
      return Unexpected{std::string{"WATCHDOG_USEC \""} + usec +
                        "\" is not a time in microseconds"};
    }
    watchdog = std::chrono::microseconds{us};
  }
  if (const char* pid = env("WATCHDOG_PID"); pid != nullptr && watchdog) {
    long long p = 0;
    if (!parse_into<long long>(pid, p, 1, 1LL << 32) || p != ::getpid()) {
      watchdog.reset();  // meant for another process (sd_watchdog_enabled(3) does the same)
    }
  }
  return to(notify_socket != nullptr ? notify_socket : "", watchdog);
}
// [/snippet:environment]

// [snippet:notify]
int ServiceManagerLink::notify(std::string_view lines) const {
  if (socket_.empty()) {
    return 0;
  }
  sockaddr_un addr{};
  addr.sun_family = AF_UNIX;
  std::memcpy(addr.sun_path, socket_.data(), socket_.size());
  if (addr.sun_path[0] == '@') {
    addr.sun_path[0] = '\0';  // an abstract address: no file, and its length is exact
  }
  const auto length = static_cast<socklen_t>(offsetof(sockaddr_un, sun_path) + socket_.size());
  // One socket per message, as sd_notify() does: a message is rare, and nothing stays open that
  // a child process could inherit.
  const int fd = ::socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    return errno;
  }
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): the sockets API's sockaddr
  const auto* dest = reinterpret_cast<const sockaddr*>(&addr);
  const auto sent = ::sendto(fd, lines.data(), lines.size(), MSG_NOSIGNAL, dest, length);
  const int err = sent < 0 ? errno : 0;
  ::close(fd);
  return err;
}
// [/snippet:notify]

int ServiceManagerLink::ready(std::string_view status) const {
  return notify("READY=1\nSTATUS=" + std::string{status});
}

int ServiceManagerLink::stopping(std::string_view status) const {
  return notify("STOPPING=1\nSTATUS=" + std::string{status});
}

int ServiceManagerLink::status(std::string_view status) const {
  return notify("STATUS=" + std::string{status});
}

Watchdog::Watchdog(const ServiceManagerLink& link, const rt::HealthMonitor& health,
                   OnChange on_change)
    : link_{link}, health_{health}, on_change_{std::move(on_change)} {
  if (const auto interval = link_.watchdog_interval(); interval) {
    period_ = *interval / 2;  // sd_watchdog_enabled(3): ping every half interval
    thread_ = std::jthread{[this](const std::stop_token& st) { run(st); }};
  }
}

Watchdog::~Watchdog() {
  thread_.request_stop();
  if (thread_.joinable()) {
    thread_.join();
  }
}

// [snippet:run]
void Watchdog::run(const std::stop_token& st) {
  bool healthy = true;
  while (!st.stop_requested()) {
    const auto silent = health_.silent();
    if (silent.empty()) {
      (void)link_.ping();  // a lost ping is caught by the next one, half an interval later
    }
    if (silent.empty() != healthy) {
      healthy = silent.empty();
      const std::string why = healthy ? std::string{"every loop beats"} : rt::describe(silent);
      (void)link_.status(healthy ? "healthy" : "unhealthy: " + why);
      if (on_change_) {
        on_change_(healthy, why);
      }
    }
    std::unique_lock lock{mu_};
    cv_.wait_for(lock, st, period_, [] { return false; });
  }
}
// [/snippet:run]

}  // namespace minidaq::control
