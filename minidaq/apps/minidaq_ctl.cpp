// SPDX-License-Identifier: MIT
// minidaq_ctl: command-line client for the control API (Chapter 6).
//
//   minidaq_ctl [OPTIONS] hello|status|start|stop|reset
//   minidaq_ctl [OPTIONS] configure acq.json
//   minidaq_ctl [OPTIONS] wait STATE [SECONDS]
//   minidaq_ctl [OPTIONS] diagnostics [EVENTS]      (API 2.1: the newest flight-recorder events)
//   minidaq_ctl new-token NAME observer|operator
//
// OPTIONS: --host 127.0.0.1, --port 7700, --token-file FILE (default: where
// minidaq_server writes its start-up token for that port), --tls-ca FILE (use
// TLS and trust the server certificates that this CA signed).
//
// Before the command, the client authenticates with the token (Chapter 17).
// new-token prints a new token on the first line and, on the second, the entry
// for the server's token file, which holds only the token's hash.
//
// Prints the server's response as indented JSON; exit status 0 if "ok" is
// true, 1 if the server refused the command, 2 on a usage or connection error.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <csignal>
#include <cstdio>
#include <exception>
#include <filesystem>
#include <fstream>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>

#include <nlohmann/json.hpp>

#include "minidaq/control/access.hpp"
#include "minidaq/control/tls.hpp"
#include "minidaq/core/parse_number.hpp"

namespace {

using nlohmann::json;

class Connection {
 public:
  Connection(const std::string& host, std::uint16_t port, const minidaq::control::TlsContext* tls)
      : fd_{::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0)} {
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    if (fd_ < 0 || ::inet_pton(AF_INET, host.c_str(), &a.sin_addr) != 1 ||
        // The sockets API takes every address family as a sockaddr*.
        ::connect(fd_, reinterpret_cast<const sockaddr*>(&a), sizeof a) != 0) {  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
      error_ = errno_text();
      return;
    }
    if (tls != nullptr) {
      auto s = minidaq::control::TlsStream::connect(*tls, fd_, host);
      if (!s) {
        error_ = s.error();
        return;
      }
      tls_.emplace(std::move(*s));
    }
  }
  ~Connection() {
    if (tls_) {
      tls_->shutdown();
    }
    if (fd_ >= 0) {
      ::close(fd_);
    }
  }
  Connection(const Connection&) = delete;
  Connection& operator=(const Connection&) = delete;
  Connection(Connection&&) = delete;
  Connection& operator=(Connection&&) = delete;
  [[nodiscard]] const std::string& error() const { return error_; }

  // Sends one request line and reads one response line.
  bool call(const json& request, json& response) {
    const std::string line = request.dump() + "\n";
    for (std::size_t sent = 0; sent < line.size();) {
      const ssize_t n = send(line.data() + sent, line.size() - sent);
      if (n <= 0) {
        return false;
      }
      sent += static_cast<std::size_t>(n);
    }
    std::size_t nl = 0;
    while ((nl = buffer_.find('\n')) == std::string::npos) {
      char buf[4096];
      const ssize_t n = receive(buf, sizeof buf);
      if (n <= 0) {
        return false;
      }
      buffer_.append(buf, static_cast<std::size_t>(n));
    }
    response = json::parse(buffer_.substr(0, nl), nullptr, false);
    buffer_.erase(0, nl + 1);
    if (!response.is_object()) {  // a discarded (unparsable) response is not an object either
      error_ = "the server's response is not a JSON object";
      return false;
    }
    return true;
  }

 private:
  // std::strerror may return a buffer shared between threads (concurrency-mt-unsafe).
  static std::string errno_text() { return std::system_category().message(errno); }

  ssize_t send(const char* data, std::size_t n) {
    if (tls_) {  // a blocking socket: done or failed, never "again"
      const auto r = tls_->write(data, n);
      if (r.io != minidaq::control::TlsStream::Io::done) {
        error_ = r.io == minidaq::control::TlsStream::Io::closed ? "connection closed by server" : tls_->error();
        return -1;
      }
      return static_cast<ssize_t>(r.bytes);
    }
    const ssize_t sent = ::send(fd_, data, n, MSG_NOSIGNAL);
    if (sent <= 0) {
      error_ = errno_text();
    }
    return sent;
  }

  ssize_t receive(char* buf, std::size_t n) {
    if (tls_) {
      const auto r = tls_->read(buf, n);
      if (r.io != minidaq::control::TlsStream::Io::done) {
        error_ = r.io == minidaq::control::TlsStream::Io::closed ? "connection closed by server" : tls_->error();
        return -1;
      }
      return static_cast<ssize_t>(r.bytes);
    }
    const ssize_t got = ::recv(fd_, buf, n, 0);
    if (got <= 0) {
      error_ = got == 0 ? "connection closed by server" : errno_text();
    }
    return got;
  }

  int fd_ = -1;
  std::optional<minidaq::control::TlsStream> tls_;
  std::string error_;
  std::string buffer_;
};

int usage(const char* argv0) {
  std::fprintf(stderr,
               "usage: %s [OPTIONS] hello|status|start|stop|reset\n"
               "       %s [OPTIONS] configure FILE.json\n"
               "       %s [OPTIONS] wait STATE [SECONDS]\n"
               "       %s [OPTIONS] diagnostics [EVENTS]\n"
               "       %s new-token NAME observer|operator\n"
               "OPTIONS: --host H, --port N, --token-file FILE, --tls-ca FILE\n",
               argv0, argv0, argv0, argv0, argv0);
  return 2;
}

// [snippet:new_token]
int new_token(const std::string& name, const std::string& role) {
  if (name.empty() || !minidaq::control::role_from_string(role)) {
    std::fprintf(stderr, "new-token: give a name and the role observer or operator\n");
    return 2;
  }
  const std::string token = minidaq::control::new_token();
  if (token.empty()) {
    std::fprintf(stderr, "new-token: no random numbers from the operating system\n");
    return 2;
  }
  // The token goes to its user; only the hash goes into the server's token file.
  std::printf("%s\n%s\n", token.c_str(),
              json{{"name", name}, {"role", role}, {"sha256", minidaq::control::token_sha256_hex(token)}}.dump().c_str());
  return 0;
}
// [/snippet:new_token]

int run(int argc, char** argv) {
  std::string host = "127.0.0.1";
  std::uint16_t port = 7700;
  std::string token_file;
  std::string ca_file;
  int i = 1;
  for (; i + 1 < argc && std::string_view{argv[i]}.starts_with("--"); i += 2) {
    const std::string_view opt{argv[i]};
    if (opt == "--host") {
      host = argv[i + 1];
    } else if (opt == "--port") {
      const auto p = minidaq::parse_number<std::uint16_t>(argv[i + 1], 1, 65535);
      if (!p) {
        std::fprintf(stderr, "--port: \"%s\" is not a port number (1 to 65535)\n", argv[i + 1]);
        return 2;
      }
      port = *p;
    } else if (opt == "--token-file") {
      token_file = argv[i + 1];
    } else if (opt == "--tls-ca") {
      ca_file = argv[i + 1];
    } else {
      return usage(argv[0]);
    }
  }
  if (i >= argc) {
    return usage(argv[0]);
  }
  const std::string cmd = argv[i];
  if (cmd == "-h" || cmd == "--help" || cmd == "help") {
    usage(argv[0]);
    return 0;
  }
  if (cmd == "new-token") {
    return i + 2 < argc ? new_token(argv[i + 1], argv[i + 2]) : usage(argv[0]);
  }
  std::optional<minidaq::control::TlsContext> tls;
  if (!ca_file.empty()) {
    auto ctx = minidaq::control::TlsContext::client(ca_file);
    if (!ctx) {
      std::fprintf(stderr, "TLS: %s\n", ctx.error().c_str());
      return 2;
    }
    tls.emplace(std::move(*ctx));
  }
  // An explicit token file must be readable; the default one may be missing
  // (a server started with --no-auth), and then the server says what it needs.
  std::string token;
  const auto path = token_file.empty() ? minidaq::control::default_token_path(port) : std::filesystem::path{token_file};
  if (!token_file.empty() || std::filesystem::exists(path)) {
    auto secret = minidaq::control::read_secret(path);
    if (!secret) {
      std::fprintf(stderr, "token: %s\n", secret.error().c_str());
      return 2;
    }
    token = std::move(*secret);
  }
  Connection conn{host, port, tls ? &*tls : nullptr};
  if (!conn.error().empty()) {
    std::fprintf(stderr, "cannot connect to %s:%u: %s\n", host.c_str(), port, conn.error().c_str());
    return 2;
  }
  json response;
  if (!token.empty()) {
    if (!conn.call(json{{"api", "2.0"}, {"id", 0}, {"cmd", "auth"}, {"token", token}}, response)) {
      std::fprintf(stderr, "%s\n", conn.error().c_str());
      return 2;
    }
    if (!response.value("ok", false)) {
      std::printf("%s\n", response.dump(2).c_str());
      return 1;
    }
  }
  if (cmd == "wait") {  // poll status until the state is reached
    if (i + 1 >= argc) {
      return usage(argv[0]);
    }
    const std::string want = argv[i + 1];
    const auto seconds = i + 2 < argc ? minidaq::parse_number<double>(argv[i + 2], 0.0, 86400.0) : 30.0;
    if (!seconds) {
      std::fprintf(stderr, "wait: \"%s\" is not a number of seconds (0 to 86400)\n", argv[i + 2]);
      return 2;
    }
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(*seconds);
    for (int id = 1;; ++id) {
      if (!conn.call(json{{"api", "2.0"}, {"id", id}, {"cmd", "status"}}, response)) {
        std::fprintf(stderr, "%s\n", conn.error().c_str());
        return 2;
      }
      // A response from another program may not have this shape: value() and
      // a JSON Pointer do not throw where response["status"].value() would.
      const auto state = response.value(json::json_pointer{"/status/state"}, std::string{});
      if (state == want) {
        std::printf("%s\n", state.c_str());
        return 0;
      }
      if (std::chrono::steady_clock::now() > deadline) {
        std::fprintf(stderr, "timeout: state is %s\n", state.c_str());
        return 1;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds{100});
    }
  }
  json request{{"api", "2.0"}, {"id", 1}, {"cmd", cmd}};  // any 2.x server accepts it (ADR 0003)
  if (cmd == "configure") {
    if (i + 1 >= argc) {
      return usage(argv[0]);
    }
    const std::ifstream in{argv[i + 1]};
    std::stringstream text;
    text << in.rdbuf();
    request["config"] = json::parse(text.str(), nullptr, false, true);
    if (!in || request["config"].is_discarded()) {
      std::fprintf(stderr, "%s: cannot read or not valid JSON\n", argv[i + 1]);
      return 2;
    }
  }
  if (cmd == "diagnostics") {
    request["api"] = "2.1";  // a 2.0 server answers unknown_command
    if (i + 1 < argc) {
      const auto n = minidaq::parse_number<std::uint64_t>(argv[i + 1], 0, 1024);
      if (!n) {
        std::fprintf(stderr, "diagnostics: \"%s\" is not a number of events (0 to 1024)\n", argv[i + 1]);
        return 2;
      }
      request["events"] = *n;
    }
  }
  if (!conn.call(request, response)) {
    std::fprintf(stderr, "%s\n", conn.error().c_str());
    return 2;
  }
  std::printf("%s\n", response.dump(2).c_str());
  return response.value("ok", false) ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  // A server that closes the connection must not end the client with SIGPIPE: the write fails instead.
  (void)std::signal(SIGPIPE, SIG_IGN);
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {  // e.g. std::bad_alloc, or a JSON error not foreseen above
    std::fprintf(stderr, "minidaq_ctl: %s\n", e.what());
    return 2;
  }
}
