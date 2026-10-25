// SPDX-License-Identifier: MIT
// MiniDAQ - TLS for the control API (Chapter 17, ADR 0014), on OpenSSL 3.
//
// TLS 1.3 only: every cipher suite it allows gives forward secrecy and
// authenticated encryption, so there is nothing to configure and nothing to get
// wrong. The server presents a certificate; the client checks it against a CA
// file it trusts and against the name or address it connected to. Client
// certificates are not used: clients prove who they are with a token
// (access.hpp), inside the encrypted connection.
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>

#include "minidaq/core/expected.hpp"

// OpenSSL's types, declared here so that no OpenSSL header leaks into users.
struct ssl_ctx_st;
struct ssl_st;

namespace minidaq::control {

class TlsContext {
 public:
  // A server's context: its certificate chain and private key, in PEM files.
  [[nodiscard]] static Expected<TlsContext, std::string> server(const std::string& cert_file,
                                                                const std::string& key_file);
  // A client's context: the CA certificates it trusts, in a PEM file.
  [[nodiscard]] static Expected<TlsContext, std::string> client(const std::string& ca_file);

  [[nodiscard]] ssl_ctx_st* native() const noexcept { return ctx_.get(); }

 private:
  struct Free {
    void operator()(ssl_ctx_st* c) const noexcept;
  };
  explicit TlsContext(ssl_ctx_st* c) : ctx_{c} {}
  std::unique_ptr<ssl_ctx_st, Free> ctx_;
};

// One TLS connection over a socket that the caller owns and closes.
class TlsStream {
 public:
  enum class Io : std::uint8_t { done, want_read, want_write, closed, error };
  struct Result {
    Io io = Io::error;
    std::size_t bytes = 0;
  };

  // The server's side of a connection on a non-blocking socket; call handshake()
  // until it is done.
  [[nodiscard]] static Expected<TlsStream, std::string> accept(const TlsContext& ctx, int fd);
  // The client's side on a blocking socket: connects and verifies the server's
  // certificate for `host`, a DNS name or an IP address.
  [[nodiscard]] static Expected<TlsStream, std::string> connect(const TlsContext& ctx, int fd,
                                                                const std::string& host);

  [[nodiscard]] Result handshake();
  [[nodiscard]] Result read(char* buf, std::size_t n);
  [[nodiscard]] Result write(const char* buf, std::size_t n);
  // Bytes already decrypted and waiting: poll() does not see them on the socket.
  [[nodiscard]] bool pending() const;
  // Sends close_notify, best effort.
  void shutdown();
  // The reason for the last error, from OpenSSL's queue.
  [[nodiscard]] const std::string& error() const noexcept { return error_; }

 private:
  struct Free {
    void operator()(ssl_st* s) const noexcept;
  };
  explicit TlsStream(ssl_st* s) : ssl_{s} {}
  Result result(int ret);
  std::unique_ptr<ssl_st, Free> ssl_;
  std::string error_;
};

}  // namespace minidaq::control
