// SPDX-License-Identifier: MIT
// A blocking control API client for the tests (Chapters 6 and 17): plain TCP,
// or TLS when given a client context. One JSON request per line, one response
// per line, "" when the server closed the connection or did not answer in 5 s.
#pragma once

#include <arpa/inet.h>
#include <csignal>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include <nlohmann/json.hpp>

#include "minidaq/control/tls.hpp"

namespace minidaq::test_support {

class Client {
 public:
  explicit Client(std::uint16_t port, const control::TlsContext* tls = nullptr, std::string host = "127.0.0.1") {
    ::signal(SIGPIPE, SIG_IGN);  // a test writes to connections that the server has closed
    fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    ::inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    ok_ = ::connect(fd_, reinterpret_cast<const sockaddr*>(&a), sizeof a) == 0;
    timeval tv{5, 0};
    ::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    if (ok_ && tls != nullptr) {
      auto s = control::TlsStream::connect(*tls, fd_, host);
      ok_ = s.has_value();
      if (s) {
        tls_.emplace(std::move(*s));
      } else {
        error_ = s.error();
      }
    }
  }
  ~Client() { close(); }
  Client(const Client&) = delete;
  Client& operator=(const Client&) = delete;
  void close() {
    tls_.reset();
    if (fd_ >= 0) {
      ::close(fd_);
      fd_ = -1;
    }
  }
  [[nodiscard]] bool ok() const { return ok_; }
  [[nodiscard]] const std::string& error() const { return error_; }
  void send(std::string_view s) {
    if (tls_) {
      (void)tls_->write(s.data(), s.size());
    } else {
      (void)::send(fd_, s.data(), s.size(), MSG_NOSIGNAL);
    }
  }
  // One response line, or "" on timeout or close.
  std::string line() {
    std::size_t nl;
    while ((nl = buf_.find('\n')) == std::string::npos) {
      char b[4096];
      std::size_t got = 0;
      if (tls_) {
        const auto r = tls_->read(b, sizeof b);
        if (r.io != control::TlsStream::Io::done) {
          return "";
        }
        got = r.bytes;
      } else {
        const ssize_t n = ::recv(fd_, b, sizeof b, 0);
        if (n <= 0) {
          return "";
        }
        got = static_cast<std::size_t>(n);
      }
      buf_.append(b, got);
    }
    std::string l = buf_.substr(0, nl);
    buf_.erase(0, nl + 1);
    return l;
  }
  nlohmann::json call(const nlohmann::json& req) {
    send(req.dump() + "\n");
    const std::string l = line();
    return l.empty() ? nlohmann::json{} : nlohmann::json::parse(l);
  }
  // Authenticates; true if the server accepted the token.
  bool auth(const std::string& token) { return call({{"cmd", "auth"}, {"token", token}}).value("ok", false); }

 private:
  int fd_ = -1;
  bool ok_ = false;
  std::optional<control::TlsStream> tls_;
  std::string error_;
  std::string buf_;
};

}  // namespace minidaq::test_support
