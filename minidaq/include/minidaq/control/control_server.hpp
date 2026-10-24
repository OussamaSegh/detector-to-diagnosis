// SPDX-License-Identifier: MIT
// MiniDAQ - TCP server for the control protocol (Chapter 6).
//
// One thread, poll(), non-blocking sockets: the control plane is low-rate and
// must never compete with the acquisition threads. Binds to 127.0.0.1 by
// default; there is no authentication yet (Chapter 17), so exposing it on a
// network interface is a deliberate configuration decision. Clients may come
// and go at any time: a disconnect is recorded in the audit trail and changes
// nothing else.
#pragma once

#include <atomic>
#include <cstdint>
#include <string>
#include <thread>

#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/core/expected.hpp"

namespace minidaq::control {

class ControlServer {
 public:
  ControlServer(AcquisitionService& service, std::uint16_t port, std::string bind_address = "127.0.0.1",
                std::size_t max_clients = 8);
  ~ControlServer();
  ControlServer(const ControlServer&) = delete;
  ControlServer& operator=(const ControlServer&) = delete;

  // Binds and starts serving; returns the port (useful with port 0).
  [[nodiscard]] Expected<std::uint16_t, std::string> start();
  void stop();
  [[nodiscard]] std::size_t clients() const noexcept { return clients_.load(std::memory_order_relaxed); }

 private:
  void run(std::stop_token st);

  AcquisitionService& service_;
  std::uint16_t port_;
  std::string bind_address_;
  std::size_t max_clients_;
  int listen_fd_ = -1;
  int wake_fd_ = -1;  // eventfd: wakes poll() on stop()
  std::atomic<std::size_t> clients_{0};
  std::jthread thread_;
};

}  // namespace minidaq::control
