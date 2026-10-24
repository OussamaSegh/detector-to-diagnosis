// SPDX-License-Identifier: MIT
// minidaq_server: the acquisition service behind the TCP control API (Chapter 6).
//
//   minidaq_server [--port 7700] [--bind 127.0.0.1] [--audit audit.jsonl] [--config acq.json]
//
// Runs until SIGINT or SIGTERM; a running acquisition is stopped and drained
// first. Control it with minidaq_ctl, or with any client that writes one JSON
// object per line to the socket.
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/audit_log.hpp"
#include "minidaq/control/control_server.hpp"

int main(int argc, char** argv) {
  using namespace minidaq;
  std::uint16_t port = 7700;
  std::string bind = "127.0.0.1";
  std::string audit_path;
  std::string config_path;
  for (int i = 1; i < argc; i += 2) {  // every option takes a value
    const std::string_view a{argv[i]};
    const char* v = i + 1 < argc ? argv[i + 1] : nullptr;
    if (a == "--port" && v) {
      port = static_cast<std::uint16_t>(std::atoi(v));
    } else if (a == "--bind" && v) {
      bind = v;
    } else if (a == "--audit" && v) {
      audit_path = v;
    } else if (a == "--config" && v) {
      config_path = v;
    } else {
      std::fprintf(stderr, "usage: %s [--port N] [--bind ADDR] [--audit FILE] [--config FILE]\n", argv[0]);
      return 2;
    }
  }

  // Block the signals before any thread starts, so that only sigwait() below sees them.
  sigset_t signals;
  sigemptyset(&signals);
  sigaddset(&signals, SIGINT);
  sigaddset(&signals, SIGTERM);
  pthread_sigmask(SIG_BLOCK, &signals, nullptr);

  std::unique_ptr<control::JsonLinesAuditLog> audit;
  control::ServiceOptions opt = control::with_default_adapters();
  if (!audit_path.empty()) {
    audit = std::make_unique<control::JsonLinesAuditLog>(audit_path);
    if (!audit->is_open()) {
      std::fprintf(stderr, "cannot open audit trail %s\n", audit_path.c_str());
      return 1;
    }
    opt.audit = audit->sink();
  }
  control::AcquisitionService service{opt};
  if (!config_path.empty()) {
    std::ifstream in{config_path};
    std::stringstream text;
    text << in.rdbuf();
    auto cfg = config::parse_config(text.str());
    if (!in || !cfg) {
      std::fprintf(stderr, "%s:\n%s", config_path.c_str(),
                   in ? config::format_errors(cfg.error()).c_str() : "cannot read\n");
      return 1;
    }
    const auto r = service.configure(*cfg, "command line");
    if (!r.ok) {
      std::fprintf(stderr, "%s\n", r.message.c_str());
      return 1;
    }
  }
  control::ControlServer server{service, port, bind};
  const auto bound = server.start();
  if (!bound) {
    std::fprintf(stderr, "control server: %s\n", bound.error().c_str());
    return 1;
  }
  std::printf("minidaq_server: control API on %s:%u (state %s)\n", bind.c_str(), *bound,
              std::string{to_string(service.state())}.c_str());
  std::fflush(stdout);

  int sig = 0;
  sigwait(&signals, &sig);
  std::printf("minidaq_server: signal %d, shutting down\n", sig);
  server.stop();
  if (service.state() == control::AcqState::running) {
    (void)service.stop("signal");
    (void)service.wait_for(control::AcqState::configured, std::chrono::seconds{10});
  }
  service.note("signal", "shutdown", "signal " + std::to_string(sig));
  return 0;
}
