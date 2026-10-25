// SPDX-License-Identifier: MIT
// MiniDAQ - TCP server for the control protocol (Chapter 6).
//
// One thread, poll(), non-blocking sockets: the control plane is low-rate and
// must never compete with the acquisition threads. Clients may come and go at
// any time: a disconnect is recorded in the audit trail and changes nothing
// else.
//
// Security (Chapter 17, ADR 0014): a client authenticates with a token before
// any command but hello, and a connection that has not done so within the
// deadline, or that offers an unknown token, is closed. TLS 1.3 protects the
// connection. The server refuses to start in a configuration that would let an
// unauthenticated or unencrypted client reach it from the network: without TLS
// and tokens it binds only to a loopback address, and without tokens only if
// the caller says so explicitly.
#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <thread>

#include "minidaq/control/access.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/tls.hpp"
#include "minidaq/core/expected.hpp"

namespace minidaq::control {

// [snippet:security]
struct ServerSecurity {
  std::shared_ptr<const TokenStore> tokens;  // who may connect; null: nobody checks
  std::shared_ptr<const TlsContext> tls;     // the server's certificate; null: plain TCP
  // Only with this set does a server without tokens start, and only on loopback.
  bool allow_unauthenticated = false;
  // A connection that has not authenticated by then is closed (it holds a client slot).
  std::chrono::milliseconds auth_deadline{10'000};
};
// [/snippet:security]

class ControlServer {
 public:
  ControlServer(AcquisitionService& service, std::uint16_t port, ServerSecurity security,
                std::string bind_address = "127.0.0.1", std::size_t max_clients = 8);
  ~ControlServer();
  ControlServer(const ControlServer&) = delete;
  ControlServer& operator=(const ControlServer&) = delete;
  ControlServer(ControlServer&&) = delete;
  ControlServer& operator=(ControlServer&&) = delete;

  // Checks the security configuration, binds and starts serving; returns the
  // port (useful with port 0).
  [[nodiscard]] Expected<std::uint16_t, std::string> start();
  void stop();
  [[nodiscard]] std::size_t clients() const noexcept { return clients_.load(std::memory_order_relaxed); }

 private:
  void run(const std::stop_token& st);

  AcquisitionService& service_;
  std::uint16_t port_;
  std::string bind_address_;
  ServerSecurity security_;
  std::size_t max_clients_;
  int listen_fd_ = -1;
  int wake_fd_ = -1;  // eventfd: wakes poll() on stop()
  std::atomic<std::size_t> clients_{0};
  std::jthread thread_;
};

}  // namespace minidaq::control
