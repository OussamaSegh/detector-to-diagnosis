// SPDX-License-Identifier: MIT
// minidaq_server: the acquisition service behind the TCP control API (Chapter 6).
//
//   minidaq_server [--port 7700] [--bind 127.0.0.1] [--audit audit.jsonl] [--config acq.json]
//                  [--tokens tokens.json] [--tls-cert cert.pem --tls-key key.pem] [--no-auth]
//                  [--crash-report FILE] [--hardware FILE]
//
// Clients authenticate with a token (Chapter 17). With --tokens, the server
// accepts the tokens whose hashes that file lists; without it, the server makes
// one operator token at start-up and writes it where minidaq_ctl looks for it,
// readable only by this user, and removes it at shutdown. --no-auth turns
// authentication off, for a test bench on loopback only. Binding to anything
// but loopback needs --tls-cert, --tls-key and --tokens.
//
// If the server dies of a fatal signal, it first writes a crash report (Chapter 21): to FILE,
// appended, with --crash-report, otherwise to standard error. It then dies of the same signal,
// with a core dump where the system keeps them (tools/postmortem.sh reads it).
//
// With --hardware, the server runs the slow control of the front-end boards that FILE describes
// (Chapter 22, minidaq/config/hardware_config.hpp) from start-up to shutdown: a run starts only
// when every board is ready, the boards' triggers follow the run (Chapter 24), a hardware fault
// stops it, and at shutdown every bias is switched off.
//
// Under systemd (Chapter 25, packaging/systemd/minidaq.service), the server says READY once its
// control API is listening and STOPPING at shutdown, and, with WatchdogSec=, pings the watchdog
// only while its loops beat: the acquisition service's monitor, the control server and the
// slow control. A loop that stops makes systemd kill the server, which writes its crash report,
// and start it again. Changes of health go to the audit trail.
//
// Runs until SIGINT or SIGTERM; a running acquisition is stopped and drained
// first. Control it with minidaq_ctl, or with any client that writes one JSON
// object per line to the socket.
#include <fcntl.h>

#include <csignal>
#include <cstdio>
#include <exception>
#include <filesystem>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/config/hardware_config.hpp"
#include "minidaq/control/access.hpp"
#include "minidaq/control/acquisition_service.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/audit_log.hpp"
#include "minidaq/control/control_server.hpp"
#include "minidaq/control/file_ops.hpp"
#include "minidaq/control/hardware.hpp"
#include "minidaq/control/service_manager.hpp"
#include "minidaq/control/tls.hpp"
#include "minidaq/core/parse_number.hpp"
#include "minidaq/rt/crash_report.hpp"
#include "minidaq/rt/health.hpp"

#ifndef MINIDAQ_VERSION_STRING
#define MINIDAQ_VERSION_STRING "unknown"
#endif

int main(int argc, char** argv) {
  using namespace minidaq;
  std::uint16_t port = 7700;
  std::string bind = "127.0.0.1";
  std::string audit_path;
  std::string config_path;
  std::string tokens_path;
  std::string cert_path;
  std::string key_path;
  std::string crash_path;
  std::string hardware_path;
  bool no_auth = false;
  for (int i = 1; i < argc; ++i) {
    const std::string_view a{argv[i]};
    if (a == "--no-auth") {
      no_auth = true;
      continue;
    }
    const char* v = i + 1 < argc ? argv[++i] : nullptr;  // every other option takes a value
    if (a == "--port" && v) {
      if (!parse_into<std::uint16_t>(v, port, 0, 65535)) {  // 0: any free port (tests use it)
        std::fprintf(stderr, "--port: \"%s\" is not a port number (0 to 65535)\n", v);
        return 2;
      }
    } else if (a == "--bind" && v) {
      bind = v;
    } else if (a == "--audit" && v) {
      audit_path = v;
    } else if (a == "--config" && v) {
      config_path = v;
    } else if (a == "--tokens" && v) {
      tokens_path = v;
    } else if (a == "--tls-cert" && v) {
      cert_path = v;
    } else if (a == "--tls-key" && v) {
      key_path = v;
    } else if (a == "--crash-report" && v) {
      crash_path = v;
    } else if (a == "--hardware" && v) {
      hardware_path = v;
    } else {
      std::fprintf(stderr,
                   "usage: %s [--port N] [--bind ADDR] [--audit FILE] [--config FILE]\n"
                   "          [--tokens FILE] [--tls-cert FILE --tls-key FILE] [--no-auth]\n"
                   "          [--crash-report FILE] [--hardware FILE]\n",
                   argv[0]);
      return 2;
    }
  }
  if (no_auth && !tokens_path.empty()) {
    std::fprintf(stderr, "--no-auth and --tokens contradict each other\n");
    return 2;
  }
  if (cert_path.empty() != key_path.empty()) {
    std::fprintf(stderr, "--tls-cert and --tls-key go together\n");
    return 2;
  }

  // [snippet:crash_report]
  // First, before any thread: the handler's alternate stack serves this thread, and every
  // thread started later inherits the handler.
  int crash_fd = 2;  // standard error: the service manager's journal keeps it
  if (!crash_path.empty()) {
    // NOLINTNEXTLINE(cppcoreguidelines-pro-type-vararg): open(2) is variadic
    crash_fd = ::open(crash_path.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    if (crash_fd < 0) {
      std::fprintf(stderr, "cannot open the crash report file %s\n", crash_path.c_str());
      return 1;
    }
  }
  if (auto installed = rt::install_crash_report(crash_fd, MINIDAQ_VERSION_STRING); !installed) {
    std::fprintf(stderr, "crash report: %s\n", installed.error().message().c_str());
    return 1;
  }
  // [/snippet:crash_report]

  // [snippet:security]
  control::ServerSecurity security;
  std::string startup_token;  // made here when no token file is given; written once the port is known
  if (!tokens_path.empty()) {
    auto store = control::TokenStore::load(tokens_path);
    if (!store) {
      std::fprintf(stderr, "tokens: %s\n", store.error().c_str());
      return 1;
    }
    security.tokens = std::make_shared<const control::TokenStore>(std::move(*store));
  } else if (no_auth) {
    security.allow_unauthenticated = true;
  } else {
    startup_token = control::new_token();
    if (startup_token.empty()) {
      std::fprintf(stderr, "cannot make a token: no random numbers from the operating system\n");
      return 1;
    }
    security.tokens = std::make_shared<const control::TokenStore>(
        control::TokenStore::single("local", control::Role::operator_, startup_token));
  }
  if (!cert_path.empty()) {
    auto tls = control::TlsContext::server(cert_path, key_path);
    if (!tls) {
      std::fprintf(stderr, "TLS: %s\n", tls.error().c_str());
      return 1;
    }
    security.tls = std::make_shared<const control::TlsContext>(std::move(*tls));
  }
  // [/snippet:security]

  auto manager = control::ServiceManagerLink::from_environment();
  if (!manager) {
    std::fprintf(stderr, "service manager: %s\n", manager.error().c_str());
    return 1;
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
  if (!hardware_path.empty()) {
    const std::ifstream in{hardware_path};
    std::stringstream text;
    text << in.rdbuf();
    auto hw = config::parse_hardware_config(text.str());
    if (!in || !hw) {
      std::fprintf(stderr, "%s:\n%s", hardware_path.c_str(),
                   in ? config::format_errors(hw.error()).c_str() : "cannot read\n");
      return 1;
    }
    auto opened = control::SlowControlHardware::open(*hw);
    if (!opened) {
      std::fprintf(stderr, "hardware: %s\n", opened.error().c_str());
      return 1;
    }
    opt.hardware = std::shared_ptr<control::HardwarePort>(std::move(*opened));
    opt.trigger_timeout = hw->trigger_timeout;  // Chapter 24
    opt.drain_timeout = hw->drain_timeout;
  }
  control::AcquisitionService service{opt};
  if (!config_path.empty()) {
    const std::ifstream in{config_path};
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
  control::ControlServer server{service, port, security, bind};
  const auto bound = server.start();
  if (!bound) {
    std::fprintf(stderr, "control server: %s\n", bound.error().c_str());
    return 1;
  }
  std::filesystem::path token_file;
  if (!startup_token.empty()) {
    auto written = control::write_secret(control::default_token_path(*bound), startup_token);
    if (!written) {
      std::fprintf(stderr, "cannot write the token: %s\n", written.error().c_str());
      return 1;
    }
    token_file = *written;
  }
  const std::string auth = !token_file.empty() ? "token in " + token_file.string()
                           : security.tokens    ? std::string{"tokens from "} + tokens_path
                                                : std::string{"NO AUTHENTICATION"};
  std::printf("minidaq_server: control API on %s:%u (%s, %s; state %s)\n", bind.c_str(), *bound,
              security.tls ? "TLS" : "plain TCP", auth.c_str(), std::string{to_string(service.state())}.c_str());
  (void)std::fflush(stdout);  // a line for a human or a test harness; nothing to do if it fails

  // [snippet:watchdog]
  // Chapter 25: what must keep beating for the process to be healthy. A loop gets its silence
  // limit to start; the limits are several times each loop's own period, so that a busy moment
  // is not a hang.
  rt::HealthMonitor health;
  health.watch("acquisition service", service.heartbeat(), std::chrono::seconds{2});
  health.watch("control server", server.heartbeat(), std::chrono::seconds{5});
  if (opt.hardware && opt.hardware->heartbeat()) {
    health.watch("slow control", opt.hardware->heartbeat(), std::chrono::seconds{3});
  }
  // READY first: the watchdog thread pings at once, and systemd should hear that the server is
  // up before it hears that the server is alive.
  if (const int err = manager->ready("state " + std::string{to_string(service.state())}); err != 0) {
    std::fprintf(stderr, "minidaq_server: READY not sent to %s: %s\n", manager->socket().c_str(),
                 control::errno_message(err).c_str());
  }
  const control::Watchdog watchdog{*manager, health, [&service](bool healthy, const std::string& why) {
                                     service.note("watchdog", healthy ? "healthy" : "unhealthy", why, healthy);
                                   }};
  // [/snippet:watchdog]

  int sig = 0;
  if (sigwait(&signals, &sig) != 0) {  // fails only for an invalid set
    std::fprintf(stderr, "sigwait failed\n");
  }
  std::printf("minidaq_server: signal %d, shutting down\n", sig);
  (void)manager->stopping("signal " + std::to_string(sig));  // nothing to do if it is lost
  server.stop();
  if (!token_file.empty()) {
    std::error_code ignored;  // a token file left behind is useless once the server is gone
    std::filesystem::remove(token_file, ignored);
  }
  if (service.state() == control::AcqState::running) {
    (void)service.stop("signal");
    (void)service.wait_for(control::AcqState::configured, std::chrono::seconds{10});
  }
  service.note("signal", "shutdown", "signal " + std::to_string(sig));
  if (audit && audit->failed_writes() > 0) {
    std::fprintf(stderr, "minidaq_server: %llu audit records could not be written to %s\n",
                 static_cast<unsigned long long>(audit->failed_writes()), audit_path.c_str());
    return 1;
  }
  return 0;
}
