// SPDX-License-Identifier: MIT
#include "minidaq/control/control_server.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/eventfd.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <map>
#include <system_error>
#include <vector>

#include "minidaq/control/control_protocol.hpp"

namespace minidaq::control {

namespace {

struct Client {
  LineFramer framer;
  std::string out;     // responses not yet sent
  std::string name;    // "tcp:127.0.0.1:50422"
  bool closing = false;  // close once `out` is sent
};

std::string peer_name(const sockaddr_in& a) {
  char ip[INET_ADDRSTRLEN] = {};
  ::inet_ntop(AF_INET, &a.sin_addr, ip, sizeof ip);
  return "tcp:" + std::string{ip} + ":" + std::to_string(ntohs(a.sin_port));
}

std::string errno_text(const char* what) { return std::string{what} + ": " + std::system_category().message(errno); }

// The sockets API takes every address family through a sockaddr*.
sockaddr* as_sockaddr(sockaddr_in* a) { return reinterpret_cast<sockaddr*>(a); }  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast)

}  // namespace

ControlServer::ControlServer(AcquisitionService& service, std::uint16_t port, std::string bind_address,
                             std::size_t max_clients)
    : service_{service}, port_{port}, bind_address_{std::move(bind_address)}, max_clients_{max_clients} {}

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
  listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
  if (listen_fd_ < 0) {
    return Unexpected{errno_text("socket")};
  }
  const int one = 1;
  // Restart without waiting for TIME_WAIT; a failure only delays a restart.
  (void)::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port_);
  if (::inet_pton(AF_INET, bind_address_.c_str(), &addr.sin_addr) != 1) {
    return Unexpected{"bad bind address \"" + bind_address_ + "\""};
  }
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
  service_.note("server", "listen", bind_address_ + ":" + std::to_string(port_));
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
  std::map<int, Client> connections;
  std::vector<pollfd> fds;
  while (!st.stop_requested()) {
    fds.clear();
    fds.push_back({listen_fd_, POLLIN, 0});
    fds.push_back({wake_fd_, POLLIN, 0});
    for (const auto& [fd, c] : connections) {
      fds.push_back({fd, static_cast<short>(POLLIN | (c.out.empty() ? 0 : POLLOUT)), 0});
    }
    if (::poll(fds.data(), fds.size(), 1000) < 0 && errno != EINTR) {
      break;
    }
    if ((fds[0].revents & POLLIN) != 0) {
      sockaddr_in peer{};
      socklen_t len = sizeof peer;
      const int fd = ::accept4(listen_fd_, as_sockaddr(&peer), &len, SOCK_NONBLOCK | SOCK_CLOEXEC);
      if (fd >= 0) {
        Client c;
        c.name = peer_name(peer);
        if (connections.size() >= max_clients_) {
          c.out = R"({"api":"1.0","id":null,"ok":false,"error":{"code":"busy","message":"too many clients"}})" "\n";
          c.closing = true;
          service_.note(c.name, "connect", "refused: too many clients", false);
        } else {
          const int one = 1;
          // Small responses go out at once; a failure only adds latency.
          (void)::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
          service_.note(c.name, "connect", "");
        }
        connections.emplace(fd, std::move(c));
      }
    }
    for (std::size_t i = 2; i < fds.size(); ++i) {
      const int fd = fds[i].fd;
      Client& c = connections.at(fd);
      bool drop = (fds[i].revents & (POLLERR | POLLNVAL)) != 0;
      if (!drop && (fds[i].revents & (POLLIN | POLLHUP)) != 0 && !c.closing) {
        char buf[4096];
        const ssize_t n = ::recv(fd, buf, sizeof buf, 0);
        if (n > 0) {
          c.framer.feed({buf, static_cast<std::size_t>(n)});
          while (auto line = c.framer.next()) {
            c.out += handle_request(*line, service_, c.name);
            c.out += '\n';
          }
          if (c.framer.overflowed()) {
            c.out += R"({"api":"1.0","id":null,"ok":false,"error":{"code":"bad_request","message":"request too long"}})" "\n";
            c.closing = true;
            service_.note(c.name, "disconnect", "request too long", false);
          }
        } else if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)) {
          drop = true;  // orderly close or error
        }
      }
      if (!drop && !c.out.empty()) {
        const ssize_t n = ::send(fd, c.out.data(), c.out.size(), MSG_NOSIGNAL);
        if (n > 0) {
          c.out.erase(0, static_cast<std::size_t>(n));
        } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
          drop = true;
        }
      }
      if (drop || (c.closing && c.out.empty())) {
        if (!c.closing) {
          service_.note(c.name, "disconnect", "");
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
