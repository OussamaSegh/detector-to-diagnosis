// SPDX-License-Identifier: MIT
#include "minidaq/control/tls.hpp"

#include <arpa/inet.h>
#include <openssl/err.h>
#include <openssl/ssl.h>
#include <openssl/x509v3.h>

#include <array>
#include <string>

namespace minidaq::control {

namespace {

// Every error OpenSSL queued, oldest first; the queue is per thread and is emptied.
std::string drain_errors(const std::string& what) {
  std::string out = what;
  for (unsigned long e = ERR_get_error(); e != 0; e = ERR_get_error()) {
    std::array<char, 256> buf{};
    ERR_error_string_n(e, buf.data(), buf.size());
    out += out.empty() ? "" : ": ";
    out += buf.data();
  }
  return out;
}

// [snippet:context]
SSL_CTX* new_context(const SSL_METHOD* method) {
  SSL_CTX* ctx = SSL_CTX_new(method);
  if (ctx == nullptr) {
    return nullptr;
  }
  // TLS 1.3 only: no protocol or cipher negotiation for an attacker to downgrade.
  if (SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION) != 1) {
    SSL_CTX_free(ctx);
    return nullptr;
  }
  // Partial writes, and a retried write may come from a moved buffer (std::string grows).
  SSL_CTX_set_mode(ctx, SSL_MODE_ENABLE_PARTIAL_WRITE | SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER);
  // No session tickets or resumption: a control connection is long-lived and rare.
  SSL_CTX_set_options(ctx, SSL_OP_NO_TICKET);
  SSL_CTX_set_session_cache_mode(ctx, SSL_SESS_CACHE_OFF);
  return ctx;
}
// [/snippet:context]

}  // namespace

void TlsContext::Free::operator()(ssl_ctx_st* c) const noexcept { SSL_CTX_free(c); }
void TlsStream::Free::operator()(ssl_st* s) const noexcept { SSL_free(s); }

Expected<TlsContext, std::string> TlsContext::server(const std::string& cert_file, const std::string& key_file) {
  ERR_clear_error();
  TlsContext t{new_context(TLS_server_method())};
  if (!t.ctx_) {
    return Unexpected{drain_errors("TLS context")};
  }
  if (SSL_CTX_use_certificate_chain_file(t.ctx_.get(), cert_file.c_str()) != 1) {
    return Unexpected{drain_errors("certificate " + cert_file)};
  }
  if (SSL_CTX_use_PrivateKey_file(t.ctx_.get(), key_file.c_str(), SSL_FILETYPE_PEM) != 1) {
    return Unexpected{drain_errors("private key " + key_file)};
  }
  if (SSL_CTX_check_private_key(t.ctx_.get()) != 1) {
    return Unexpected{drain_errors("the private key does not match the certificate")};
  }
  return t;
}

Expected<TlsContext, std::string> TlsContext::client(const std::string& ca_file) {
  ERR_clear_error();
  TlsContext t{new_context(TLS_client_method())};
  if (!t.ctx_) {
    return Unexpected{drain_errors("TLS context")};
  }
  if (SSL_CTX_load_verify_locations(t.ctx_.get(), ca_file.c_str(), nullptr) != 1) {
    return Unexpected{drain_errors("CA file " + ca_file)};
  }
  SSL_CTX_set_verify(t.ctx_.get(), SSL_VERIFY_PEER, nullptr);
  return t;
}

Expected<TlsStream, std::string> TlsStream::accept(const TlsContext& ctx, int fd) {
  ERR_clear_error();
  TlsStream s{SSL_new(ctx.native())};
  if (!s.ssl_ || SSL_set_fd(s.ssl_.get(), fd) != 1) {
    return Unexpected{drain_errors("TLS session")};
  }
  SSL_set_accept_state(s.ssl_.get());
  return s;
}

// [snippet:connect]
Expected<TlsStream, std::string> TlsStream::connect(const TlsContext& ctx, int fd, const std::string& host) {
  ERR_clear_error();
  TlsStream s{SSL_new(ctx.native())};
  if (!s.ssl_ || SSL_set_fd(s.ssl_.get(), fd) != 1) {
    return Unexpected{drain_errors("TLS session")};
  }
  // The certificate must name what we connected to: an IP address in its
  // subjectAltName, or a DNS name, which is also sent as SNI.
  std::array<unsigned char, sizeof(in6_addr)> addr{};
  const bool is_ip = ::inet_pton(AF_INET, host.c_str(), addr.data()) == 1 ||
                     ::inet_pton(AF_INET6, host.c_str(), addr.data()) == 1;
  X509_VERIFY_PARAM* param = SSL_get0_param(s.ssl_.get());
  std::string sni = host;  // SSL_set_tlsext_host_name is a macro that casts away const; SSL_ctrl needs no cast
  const bool named = is_ip ? X509_VERIFY_PARAM_set1_ip_asc(param, host.c_str()) == 1
                           : SSL_set1_host(s.ssl_.get(), host.c_str()) == 1 &&
                                 SSL_ctrl(s.ssl_.get(), SSL_CTRL_SET_TLSEXT_HOSTNAME, TLSEXT_NAMETYPE_host_name,
                                          static_cast<void*>(sni.data())) == 1;
  if (!named) {
    return Unexpected{drain_errors("TLS host name " + host)};
  }
  if (SSL_connect(s.ssl_.get()) != 1) {
    const long verify = SSL_get_verify_result(s.ssl_.get());
    return Unexpected{drain_errors(verify == X509_V_OK ? std::string{"TLS handshake"}
                                                       : std::string{"certificate: "} +
                                                             X509_verify_cert_error_string(verify))};
  }
  return s;
}
// [/snippet:connect]

TlsStream::Result TlsStream::result(int ret) {
  if (ret > 0) {
    return {Io::done, static_cast<std::size_t>(ret)};
  }
  switch (SSL_get_error(ssl_.get(), ret)) {
    case SSL_ERROR_WANT_READ:
      return {Io::want_read};
    case SSL_ERROR_WANT_WRITE:
      return {Io::want_write};
    case SSL_ERROR_ZERO_RETURN:
      return {Io::closed};
    default:
      error_ = drain_errors("TLS");
      return {Io::error};
  }
}

TlsStream::Result TlsStream::handshake() {
  ERR_clear_error();
  const int ret = SSL_do_handshake(ssl_.get());
  return ret == 1 ? Result{Io::done} : result(ret);
}

TlsStream::Result TlsStream::read(char* buf, std::size_t n) {
  ERR_clear_error();
  std::size_t got = 0;
  const int ret = SSL_read_ex(ssl_.get(), buf, n, &got);
  return ret == 1 ? Result{Io::done, got} : result(ret);
}

TlsStream::Result TlsStream::write(const char* buf, std::size_t n) {
  ERR_clear_error();
  std::size_t sent = 0;
  const int ret = SSL_write_ex(ssl_.get(), buf, n, &sent);
  return ret == 1 ? Result{Io::done, sent} : result(ret);
}

bool TlsStream::pending() const { return SSL_pending(ssl_.get()) > 0; }

void TlsStream::shutdown() {
  ERR_clear_error();
  (void)SSL_shutdown(ssl_.get());  // best effort: the socket is closed next either way
  ERR_clear_error();
}

}  // namespace minidaq::control
