// SPDX-License-Identifier: MIT
// minidaq_ctl: command-line client for the control API (Chapter 6).
//
//   minidaq_ctl [--host 127.0.0.1] [--port 7700] hello|status|start|stop|reset
//   minidaq_ctl [--host H] [--port N] configure acq.json
//   minidaq_ctl [--host H] [--port N] wait STATE [SECONDS]
//
// Prints the server's response as indented JSON; exit status 0 if "ok" is
// true, 1 if the server refused the command, 2 on a usage or connection error.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <exception>
#include <fstream>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>

#include <nlohmann/json.hpp>

#include "minidaq/core/parse_number.hpp"

namespace {

using nlohmann::json;

class Connection {
 public:
  Connection(const std::string& host, std::uint16_t port) : fd_{::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0)} {
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    if (fd_ < 0 || ::inet_pton(AF_INET, host.c_str(), &a.sin_addr) != 1 ||
        // The sockets API takes every address family as a sockaddr*.
        ::connect(fd_, reinterpret_cast<const sockaddr*>(&a), sizeof a) != 0) {  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)
      error_ = errno_text();
    }
  }
  ~Connection() {
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
      const ssize_t n = ::send(fd_, line.data() + sent, line.size() - sent, MSG_NOSIGNAL);
      if (n <= 0) {
        error_ = errno_text();
        return false;
      }
      sent += static_cast<std::size_t>(n);
    }
    std::size_t nl = 0;
    while ((nl = buffer_.find('\n')) == std::string::npos) {
      char buf[4096];
      const ssize_t n = ::recv(fd_, buf, sizeof buf, 0);
      if (n <= 0) {
        error_ = n == 0 ? "connection closed by server" : errno_text();
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

  int fd_ = -1;
  std::string error_;
  std::string buffer_;
};

int usage(const char* argv0) {
  std::fprintf(stderr,
               "usage: %s [--host H] [--port N] hello|status|start|stop|reset\n"
               "       %s [--host H] [--port N] configure FILE.json\n"
               "       %s [--host H] [--port N] wait STATE [SECONDS]\n",
               argv0, argv0, argv0);
  return 2;
}

int run(int argc, char** argv) {
  std::string host = "127.0.0.1";
  std::uint16_t port = 7700;
  int i = 1;
  for (; i + 1 < argc && std::string_view{argv[i]}.starts_with("--"); i += 2) {
    if (std::string_view{argv[i]} == "--host") {
      host = argv[i + 1];
    } else if (std::string_view{argv[i]} == "--port") {
      const auto p = minidaq::parse_number<std::uint16_t>(argv[i + 1], 1, 65535);
      if (!p) {
        std::fprintf(stderr, "--port: \"%s\" is not a port number (1 to 65535)\n", argv[i + 1]);
        return 2;
      }
      port = *p;
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
  Connection conn{host, port};
  if (!conn.error().empty()) {
    std::fprintf(stderr, "cannot connect to %s:%u: %s\n", host.c_str(), port, conn.error().c_str());
    return 2;
  }
  json response;
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
      if (!conn.call(json{{"api", "1.0"}, {"id", id}, {"cmd", "status"}}, response)) {
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
  json request{{"api", "1.0"}, {"id", 1}, {"cmd", cmd}};
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
  if (!conn.call(request, response)) {
    std::fprintf(stderr, "%s\n", conn.error().c_str());
    return 2;
  }
  std::printf("%s\n", response.dump(2).c_str());
  return response.value("ok", false) ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {  // e.g. std::bad_alloc, or a JSON error not foreseen above
    std::fprintf(stderr, "minidaq_ctl: %s\n", e.what());
    return 2;
  }
}
