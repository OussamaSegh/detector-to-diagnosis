// SPDX-License-Identifier: MIT
#include "minidaq/control/control_server.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <pthread.h>
#include <sys/eventfd.h>
#include <sys/socket.h>
#include <unistd.h>

#include <array>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

#include "minidaq/control/control_protocol.hpp"

namespace minidaq::control {

namespace {

struct Client {
  LineFramer framer;
  std::string out;     // responses not yet sent
  Session session;     // the peer's name and, once authenticated, its identity
  bool closing = false;  // close once `out` is sent
  std::optional<TlsStream> tls;
  bool handshaken = false;  // the TLS handshake is complete (always, without TLS)
  bool tls_wants_write = false;  // the last TLS call needs the socket writable
  std::chrono::steady_clock::time_point deadline;  // to authenticate
};

// Reads what the socket or the TLS stream has. 0 for an orderly close, -1 for
// an error, otherwise the bytes (possibly none yet).
ssize_t receive(Client& c, int fd, char* buf, std::size_t n) {
  if (!c.tls) {
    const ssize_t got = ::recv(fd, buf, n, 0);
    if (got < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
      return -2;
    }
    return got;
  }
  const auto r = c.tls->read(buf, n);
  c.tls_wants_write = r.io == TlsStream::Io::want_write;
  switch (r.io) {
    case TlsStream::Io::done:
      return static_cast<ssize_t>(r.bytes);
    case TlsStream::Io::want_read:
    case TlsStream::Io::want_write:
      return -2;
    case TlsStream::Io::closed:
      return 0;
    case TlsStream::Io::error:
      break;
  }
  return -1;
}

// Sends what it can of c.out; false on an error.
bool transmit(Client& c, int fd) {
  if (!c.tls) {
    const ssize_t n = ::send(fd, c.out.data(), c.out.size(), MSG_NOSIGNAL);
    if (n > 0) {
      c.out.erase(0, static_cast<std::size_t>(n));
    }
    return n >= 0 || errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR;
  }
  const auto r = c.tls->write(c.out.data(), c.out.size());
  c.tls_wants_write = r.io == TlsStream::Io::want_write;
  if (r.io == TlsStream::Io::done) {
    c.out.erase(0, r.bytes);
  }
  return r.io != TlsStream::Io::error && r.io != TlsStream::Io::closed;
}

std::string peer_name(const sockaddr_in& a) {
  char ip[INET_ADDRSTRLEN] = {};
  ::inet_ntop(AF_INET, &a.sin_addr, ip, sizeof ip);
  return "tcp:" + std::string{ip} + ":" + std::to_string(ntohs(a.sin_port));
}

std::string errno_text(const char* what) { return std::string{what} + ": " + std::system_category().message(errno); }

// A response to a connection that is refused or closed before any request is
// handled. Code and message are fixed ASCII text, so no JSON escaping is needed.
std::string refusal(std::string_view code, std::string_view message) {
  return std::string{R"({"api":")"} + std::string{api_version} + R"(","id":null,"ok":false,"error":{"code":")" +
         std::string{code} + R"(","message":")" + std::string{message} + "\"}}\n";
}

// The sockets API takes every address family through a sockaddr*.
sockaddr* as_sockaddr(sockaddr_in* a) { return reinterpret_cast<sockaddr*>(a); }  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)

}  // namespace

ControlServer::ControlServer(AcquisitionService& service, std::uint16_t port, ServerSecurity security,
                             std::string bind_address, std::size_t max_clients)
    : service_{service},
      port_{port},
      bind_address_{std::move(bind_address)},
      security_{std::move(security)},
      max_clients_{max_clients} {}

ControlServer::~ControlServer() {
  stop();
  if (listen_fd_ >= 0) {
    ::close(listen_fd_);
  }
  if (wake_fd_ >= 0) {
    ::close(wake_fd_);
  }
}

Expected<std::uint16_t, std::string> ControlServer::start() {
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port_);
  if (::inet_pton(AF_INET, bind_address_.c_str(), &addr.sin_addr) != 1) {
    return Unexpected{"bad bind address \"" + bind_address_ + "\""};
  }
  // [snippet:secure_defaults]
  const bool loopback = (ntohl(addr.sin_addr.s_addr) >> 24U) == 127U;  // 127.0.0.0/8
  if (!security_.tokens && !security_.allow_unauthenticated) {
    return Unexpected{std::string{"no tokens: clients could not authenticate"}};
  }
  if (!loopback && (!security_.tokens || !security_.tls)) {
    return Unexpected{"binding to " + bind_address_ + " needs TLS and tokens: the network could reach the control API"};
  }
  // [/snippet:secure_defaults]
  listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
  if (listen_fd_ < 0) {
    return Unexpected{errno_text("socket")};
  }
  const int one = 1;
  // Restart without waiting for TIME_WAIT; a failure only delays a restart.
  (void)::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  if (::bind(listen_fd_, as_sockaddr(&addr), sizeof addr) != 0) {
    return Unexpected{errno_text("bind")};
  }
  if (::listen(listen_fd_, 8) != 0) {
    return Unexpected{errno_text("listen")};
  }
  socklen_t len = sizeof addr;
  if (::getsockname(listen_fd_, as_sockaddr(&addr), &len) != 0) {  // the port, if port_ was 0
    return Unexpected{errno_text("getsockname")};
  }
  // Without the eventfd, stop() could not wake the poll() and would wait for its timeout.
  wake_fd_ = ::eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
  if (wake_fd_ < 0) {
    return Unexpected{errno_text("eventfd")};
  }
  port_ = ntohs(addr.sin_port);  // set before the thread starts, so that the thread could read it
  thread_ = std::jthread{[this](const std::stop_token& st) { run(st); }};
  service_.note("server", "listen",
                bind_address_ + ":" + std::to_string(port_) + (security_.tls ? " tls" : " plain") +
                    (security_.tokens ? " tokens" : " unauthenticated"));
  return port_;
}

void ControlServer::stop() {
  if (thread_.joinable()) {
    thread_.request_stop();
    const std::uint64_t one = 1;
    [[maybe_unused]] const auto n = ::write(wake_fd_, &one, sizeof one);
    thread_.join();
  }
}

// [snippet:loop]
void ControlServer::run(const std::stop_token& st) {
  using clock = std::chrono::steady_clock;
  // OpenSSL writes to the socket with write(2), and a write to a connection the
  // peer has closed raises SIGPIPE, which ends the process. Blocked in this
  // thread, it stays pending instead and the write fails with EPIPE.
  sigset_t pipe;
  sigemptyset(&pipe);
  sigaddset(&pipe, SIGPIPE);
  pthread_sigmask(SIG_BLOCK, &pipe, nullptr);
  std::map<int, Client> connections;
  std::vector<pollfd> fds;

  auto accept_client = [&] {
    sockaddr_in peer{};
    socklen_t len = sizeof peer;
    const int fd = ::accept4(listen_fd_, as_sockaddr(&peer), &len, SOCK_NONBLOCK | SOCK_CLOEXEC);
    if (fd < 0) {
      return;
    }
    Client c;
    c.session.peer = peer_name(peer);
    c.deadline = clock::now() + security_.auth_deadline;
    if (!security_.tokens) {  // authentication is off (loopback only, by explicit choice)
      c.session.identity = {"unauthenticated", Role::operator_};
    }
    if (security_.tls) {
      auto s = TlsStream::accept(*security_.tls, fd);
      if (!s) {
        service_.note(c.session.peer, "connect", "refused: " + s.error(), false);
        ::close(fd);
        return;
      }
      c.tls.emplace(std::move(*s));
    } else {
      c.handshaken = true;
    }
    if (connections.size() >= max_clients_) {
      // Over TLS, the refusal goes out after the handshake.
      c.out = refusal("busy", "too many clients");
      c.closing = true;
      service_.note(c.session.peer, "connect", "refused: too many clients", false);
    } else {
      const int one = 1;
      // Small responses go out at once; a failure only adds latency.
      (void)::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
      service_.note(c.session.peer, "connect", security_.tls ? "tls" : "");
    }
    connections.emplace(fd, std::move(c));
  };

  // False if the handshake failed: a client that does not speak TLS, or rejects our certificate.
  auto handshake = [&](Client& c) {
    const auto r = c.tls->handshake();
    c.tls_wants_write = r.io == TlsStream::Io::want_write;
    if (r.io == TlsStream::Io::done) {
      c.handshaken = true;
      return true;
    }
    if (r.io == TlsStream::Io::want_read || r.io == TlsStream::Io::want_write) {
      return true;
    }
    service_.note(c.session.peer, "disconnect", "TLS handshake failed: " + c.tls->error(), false);
    c.closing = true;
    return false;
  };

  // Reads and answers what the client sent; false if the connection is gone.
  auto serve = [&](Client& c, int fd) {
    std::array<char, 4096> buf{};
    for (;;) {  // over TLS, read until the stream has nothing decrypted left
      const ssize_t n = receive(c, fd, buf.data(), buf.size());
      if (n == -2) {
        return true;  // nothing more for now
      }
      if (n <= 0) {
        return false;  // orderly close or error
      }
      c.framer.feed({buf.data(), static_cast<std::size_t>(n)});
      while (auto line = c.framer.next()) {
        c.out += handle_request(*line, service_, c.session, security_.tokens.get());
        c.out += '\n';
        if (c.session.failed_auth) {  // the auth handler recorded it
          c.closing = true;
          return true;
        }
      }
      if (c.framer.overflowed()) {
        c.out += refusal("bad_request", "request too long");
        c.closing = true;
        service_.note(c.session.who(), "disconnect", "request too long", false);
        return true;
      }
      if (!c.tls) {
        return true;  // poll() reports the socket again if more is waiting
      }
    }
  };

  while (!st.stop_requested()) {
    fds.clear();
    fds.push_back({listen_fd_, POLLIN, 0});
    fds.push_back({wake_fd_, POLLIN, 0});
    for (const auto& [fd, c] : connections) {
      const bool write = !c.out.empty() || c.tls_wants_write;
      fds.push_back({fd, static_cast<short>(POLLIN | (write ? POLLOUT : 0)), 0});
    }
    // Wake at least every 100 ms to close connections past their deadline.
    if (::poll(fds.data(), fds.size(), 100) < 0 && errno != EINTR) {
      break;
    }
    if ((fds[0].revents & POLLIN) != 0) {
      accept_client();
    }
    const auto now = clock::now();
    for (std::size_t i = 2; i < fds.size(); ++i) {
      const int fd = fds[i].fd;
      Client& c = connections.at(fd);
      bool drop = (fds[i].revents & (POLLERR | POLLNVAL)) != 0;
      const bool ready = (fds[i].revents & (POLLIN | POLLOUT | POLLHUP)) != 0 || (c.tls && c.tls->pending());
      if (!drop && ready && !c.handshaken) {
        drop = !handshake(c);
      }
      if (!drop && ready && c.handshaken && !c.closing) {
        drop = !serve(c, fd);
      }
      if (!drop && c.handshaken && (!c.out.empty() || c.tls_wants_write)) {
        drop = !transmit(c, fd);
      }
      if (!drop && now > c.deadline && (!c.handshaken || c.session.identity.role == Role::none)) {
        if (!c.closing) {
          service_.note(c.session.peer, "disconnect", "not authenticated in time", false);
          c.closing = true;
        }
        drop = true;  // no response: the client may not even speak the protocol
      }
      if (drop || (c.closing && c.out.empty())) {
        if (!drop && c.tls) {
          c.tls->shutdown();
        }
        if (!c.closing) {  // a server-side close was recorded when it was decided
          service_.note(c.session.who(), "disconnect", "");
        }
        ::close(fd);
        connections.erase(fd);
      }
    }
    clients_.store(connections.size(), std::memory_order_relaxed);
  }
  for (const auto& [fd, c] : connections) {
    ::close(fd);
  }
  clients_.store(0, std::memory_order_relaxed);
}
// [/snippet:loop]

}  // namespace minidaq::control
