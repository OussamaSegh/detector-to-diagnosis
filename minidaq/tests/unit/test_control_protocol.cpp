// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <mutex>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/adapters.hpp"
#include "minidaq/control/control_protocol.hpp"
#include "minidaq/control/control_server.hpp"

using namespace minidaq;
using namespace minidaq::control;
using nlohmann::json;
using namespace std::chrono_literals;

TEST(LineFramer, SplitsAndJoinsLikeTcpDoes) {
  LineFramer f;
  f.feed("{\"cmd\":");
  EXPECT_FALSE(f.next()) << "half a request";
  f.feed("\"status\"}\n{\"cmd\":\"hello\"}\r\n{\"cm");
  EXPECT_EQ(f.next(), R"({"cmd":"status"})");
  EXPECT_EQ(f.next(), R"({"cmd":"hello"})") << "CRLF is accepted";
  EXPECT_FALSE(f.next());
  f.feed("d\":\"stop\"}\n\n");
  EXPECT_EQ(f.next(), R"({"cmd":"stop"})");
  EXPECT_EQ(f.next(), "") << "an empty line is a (bad) request, not nothing";
  EXPECT_FALSE(f.overflowed());
}

TEST(LineFramer, AnOverlongLineIsFatal) {
  // REQ: SRS-CTL-021
  LineFramer f{16};
  f.feed("0123456789");
  EXPECT_FALSE(f.next());
  f.feed("0123456789");  // 20 bytes and still no newline
  EXPECT_FALSE(f.next());
  EXPECT_TRUE(f.overflowed());
  f.feed("\n{}\n");
  EXPECT_FALSE(f.next()) << "no resynchronization after an overflow";

  LineFramer g{16};
  g.feed(std::string(20, 'x') + "\n");
  EXPECT_FALSE(g.next());
  EXPECT_TRUE(g.overflowed()) << "also when the newline arrived in the same read";
}

namespace {
json call(AcquisitionService& svc, std::string_view line) { return json::parse(handle_request(line, svc, "test")); }
}  // namespace

TEST(ControlProtocol, CommandsAndErrors) {
  // REQ: SRS-CTL-020
  AcquisitionService svc{with_default_adapters()};
  auto r = call(svc, R"({"api":"1.0","id":"a1","cmd":"hello"})");
  EXPECT_EQ(r["ok"], true);
  EXPECT_EQ(r["id"], "a1") << "id echoed unchanged";
  EXPECT_NE(r["server"].get<std::string>().find("minidaq"), std::string::npos);

  r = call(svc, R"({"api":"1.0","id":2,"cmd":"start"})");
  EXPECT_EQ(r["ok"], false);
  EXPECT_EQ(r["error"]["code"], "illegal_transition");
  EXPECT_EQ(r["state"], "idle");

  r = call(svc, R"({"id":3,"cmd":"configure","config":{"schema_version":"1.0","pipeline":{"batchsize":1}}})");
  EXPECT_EQ(r["error"]["code"], "config_error");
  ASSERT_EQ(r["error"]["details"].size(), 1U);
  EXPECT_EQ(r["error"]["details"][0]["path"], "/pipeline/batchsize");

  r = call(svc, R"({"id":4,"cmd":"configure","config":{"schema_version":"1.0","stop_after_s":0.01,"source":{"rate_hz":1e6}}})");
  EXPECT_EQ(r["ok"], true);
  EXPECT_EQ(r["state"], "configured");
  r = call(svc, R"({"id":5,"cmd":"status"})");
  EXPECT_EQ(r["status"]["state"], "configured");
  EXPECT_EQ(r["status"]["config"]["source"]["rate_hz"], 1e6);
}

TEST(ControlProtocol, VersioningAndMalformedInput) {
  // REQ: SRS-CTL-022
  AcquisitionService svc{with_default_adapters()};
  EXPECT_EQ(call(svc, R"({"api":"2.0","id":1,"cmd":"status"})")["error"]["code"], "unsupported_api");
  EXPECT_EQ(call(svc, R"({"api":"1.7","id":1,"cmd":"status","priority":"high"})")["ok"], true)
      << "newer minor version and unknown fields are accepted";
  EXPECT_EQ(call(svc, R"({"api":2,"cmd":"status"})")["error"]["code"], "unsupported_api");
  EXPECT_EQ(call(svc, "not json")["error"]["code"], "bad_request");
  EXPECT_EQ(call(svc, "[1,2]")["error"]["code"], "bad_request");
  EXPECT_EQ(call(svc, "")["error"]["code"], "bad_request");
  EXPECT_EQ(call(svc, R"({"id":9})")["error"]["code"], "bad_request");
  EXPECT_EQ(call(svc, R"({"id":9,"cmd":"launch"})")["error"]["code"], "unknown_command");
  EXPECT_EQ(call(svc, R"({"cmd":"configure"})")["error"]["code"], "bad_request");
  const std::string bad_utf8 = "{\"cmd\":\"\xff\xfe\"}";
  EXPECT_EQ(call(svc, bad_utf8)["ok"], false) << "invalid UTF-8 is rejected, not a crash";
}

namespace {

class Client {
 public:
  explicit Client(std::uint16_t port) {
    fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(port);
    ::inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    ok_ = ::connect(fd_, reinterpret_cast<const sockaddr*>(&a), sizeof a) == 0;
    timeval tv{5, 0};
    ::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
  }
  ~Client() { close(); }
  Client(const Client&) = delete;
  Client& operator=(const Client&) = delete;
  void close() {
    if (fd_ >= 0) {
      ::close(fd_);
      fd_ = -1;
    }
  }
  [[nodiscard]] bool ok() const { return ok_; }
  void send(std::string_view s) { (void)::send(fd_, s.data(), s.size(), MSG_NOSIGNAL); }
  // One response line, or "" on timeout or close.
  std::string line() {
    std::size_t nl;
    while ((nl = buf_.find('\n')) == std::string::npos) {
      char b[4096];
      const ssize_t n = ::recv(fd_, b, sizeof b, 0);
      if (n <= 0) {
        return "";
      }
      buf_.append(b, static_cast<std::size_t>(n));
    }
    std::string l = buf_.substr(0, nl);
    buf_.erase(0, nl + 1);
    return l;
  }
  json call(const json& req) {
    send(req.dump() + "\n");
    const std::string l = line();
    return l.empty() ? json{} : json::parse(l);
  }

 private:
  int fd_ = -1;
  bool ok_ = false;
  std::string buf_;
};

}  // namespace

TEST(ControlServer, PipelinedRequestsAndManyClients) {
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0};
  const auto port = server.start();
  ASSERT_TRUE(port) << port.error();
  Client a{*port};
  Client b{*port};
  ASSERT_TRUE(a.ok() && b.ok());
  // Three requests in one write: three responses, in order.
  a.send("{\"id\":1,\"cmd\":\"hello\"}\n{\"id\":2,\"cmd\":\"status\"}\n{\"id\":3,\"cmd\":\"start\"}\n");
  EXPECT_EQ(json::parse(a.line())["id"], 1);
  EXPECT_EQ(json::parse(a.line())["id"], 2);
  EXPECT_EQ(json::parse(a.line())["id"], 3);
  EXPECT_EQ(b.call({{"id", 7}, {"cmd", "status"}})["status"]["state"], "idle");
}

TEST(ControlServer, AClientThatDisconnectsDoesNotStopTheAcquisition) {
  // REQ: SRS-CTL-023
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0};
  const auto port = server.start();
  ASSERT_TRUE(port);
  {
    Client c{*port};
    ASSERT_EQ(c.call({{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}, {"source", {{"rate_hz", 1e6}}}}}})["ok"],
              true);
    ASSERT_EQ(c.call({{"cmd", "start"}})["state"], "running");
  }  // the client goes away mid-run
  std::this_thread::sleep_for(50ms);
  EXPECT_EQ(svc.state(), AcqState::running);
  Client again{*port};
  const auto st = again.call({{"cmd", "status"}});
  EXPECT_EQ(st["status"]["state"], "running");
  EXPECT_EQ(st["status"]["run_id"], 1) << "a new client sees the same run";
  EXPECT_EQ(again.call({{"cmd", "stop"}})["ok"], true);
  EXPECT_TRUE(svc.wait_for(AcqState::configured, 5s));
}

TEST(ControlServer, RecordsEveryCommandWithTheClientsAddress) {
  // REQ: SRS-CTL-032
  std::mutex mu;
  std::vector<AuditRecord> records;
  ServiceOptions opt = with_default_adapters();
  opt.audit = [&](const AuditRecord& r) {
    const std::lock_guard lock{mu};
    records.push_back(r);
  };
  AcquisitionService svc{std::move(opt)};
  ControlServer server{svc, 0};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client c{*port};
  ASSERT_TRUE(c.ok());
  EXPECT_EQ(c.call({{"cmd", "start"}})["ok"], false);  // rejected: not configured
  EXPECT_EQ(c.call({{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}}}})["ok"], true);
  EXPECT_EQ(c.call({{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}, {"sorce", {}}}}})["ok"], false);
  EXPECT_EQ(c.call({{"cmd", "reset"}})["ok"], true);
  const std::lock_guard lock{mu};
  std::vector<std::pair<std::string, bool>> seen;
  for (const auto& r : records) {
    if (r.action != "configure" && r.action != "start" && r.action != "stop" && r.action != "reset") {
      continue;  // transitions, connections: recorded too, not commands
    }
    EXPECT_TRUE(r.who.starts_with("tcp:127.0.0.1:")) << r.action << " by " << r.who;
    seen.emplace_back(r.action, r.ok);
  }
  const std::vector<std::pair<std::string, bool>> expected{
      {"start", false}, {"configure", true}, {"configure", false}, {"reset", true}};
  EXPECT_EQ(seen, expected);
}

TEST(ControlServer, OverlongRequestClosesOnlyThatConnection) {
  // REQ: SRS-CTL-021
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client bad{*port};
  Client good{*port};
  bad.send(std::string(max_request_bytes + 10, 'x'));
  const std::string l = bad.line();
  ASSERT_FALSE(l.empty());
  EXPECT_EQ(json::parse(l)["error"]["message"], "request too long");
  EXPECT_EQ(bad.line(), "") << "then the server closes the connection";
  EXPECT_EQ(good.call({{"cmd", "hello"}})["ok"], true);
}

TEST(ControlServer, RefusesClientsBeyondTheLimit) {
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0, "127.0.0.1", 2};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client a{*port};
  Client b{*port};
  ASSERT_EQ(a.call({{"cmd", "hello"}})["ok"], true);
  ASSERT_EQ(b.call({{"cmd", "hello"}})["ok"], true);
  Client c{*port};
  const std::string l = c.line();
  ASSERT_FALSE(l.empty());
  EXPECT_EQ(json::parse(l)["error"]["code"], "busy");
}

TEST(ControlServer, BadBindAddressIsReported) {
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0, "not-an-address"};
  const auto r = server.start();
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("bad bind address"), std::string::npos);
}
