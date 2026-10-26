// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <mutex>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/adapters.hpp"
#include "minidaq/control/control_protocol.hpp"
#include "minidaq/control/control_server.hpp"
#include "minidaq/core/flight_recorder.hpp"
#include "eventually.hpp"
#include "test_client.hpp"

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
// The protocol layer alone, for a session that is already an operator.
json call(AcquisitionService& svc, std::string_view line) {
  Session s{"test", {"test", Role::operator_}};
  return json::parse(handle_request(line, svc, s, nullptr));
}
}  // namespace

TEST(ControlProtocol, CommandsAndErrors) {
  // REQ: SRS-CTL-020
  AcquisitionService svc{with_default_adapters()};
  auto r = call(svc, R"({"api":"2.0","id":"a1","cmd":"hello"})");
  EXPECT_EQ(r["ok"], true);
  EXPECT_EQ(r["id"], "a1") << "id echoed unchanged";
  EXPECT_NE(r["server"].get<std::string>().find("minidaq"), std::string::npos);

  r = call(svc, R"({"api":"2.0","id":2,"cmd":"start"})");
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
  EXPECT_EQ(call(svc, R"({"api":"3.0","id":1,"cmd":"status"})")["error"]["code"], "unsupported_api");
  EXPECT_EQ(call(svc, R"({"api":"1.1","id":1,"cmd":"status"})")["error"]["code"], "unsupported_api")
      << "a 1.x client does not authenticate, so 2.0 refuses it (ADR 0014)";
  EXPECT_EQ(call(svc, R"({"api":"2.7","id":1,"cmd":"status","priority":"high"})")["ok"], true)
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

// [snippet:type_confusion]
TEST(ControlProtocol, EveryFieldOfEveryTypeIsAnswered) {
  // REQ: SRS-CTL-034
  // MDQ-PR-013: {"cmd":"auth","token":5} threw out of handle_request and ended the server. Each
  // field the protocol reads gets every JSON type, for every command and every kind of client.
  AcquisitionService svc{with_default_adapters()};
  const TokenStore tokens = TokenStore::single("op", Role::operator_, new_token());
  const std::vector<std::string> commands{"hello", "auth", "status", "configure", "start",
                                          "stop",  "reset", "launch", "diagnostics"};
  const std::vector<std::string> fields{"api", "id", "cmd", "token", "config", "events"};
  const std::vector<json> values{5, -1, 1.5, "x", "2.0", nullptr, true,
                                 json::array(), json::array({1}), json::object(), json{{"a", 1}}};
  const std::vector<Identity> clients{{}, {"op", Role::operator_}, {"obs", Role::observer}};
  int requests = 0;
  for (const auto& cmd : commands) {
    for (const auto& field : fields) {
      for (const auto& value : values) {
        for (std::size_t k = 0; k <= clients.size(); ++k) {
          json req{{"api", "2.0"}, {"id", 1}, {"cmd", cmd}};
          req[field] = value;
          const bool no_auth = k == clients.size();  // the last: a server started with --no-auth
          Session s{"test", no_auth ? Identity{"local", Role::operator_} : clients[k]};
          const TokenStore* store = no_auth ? nullptr : &tokens;
          std::string out;
          ASSERT_NO_THROW(out = handle_request(req.dump(), svc, s, store)) << req.dump();
          EXPECT_EQ(out.find('\n'), std::string::npos) << req.dump();
          const auto r = json::parse(out, nullptr, false);
          ASSERT_TRUE(r.is_object() && r.contains("ok") && r["ok"].is_boolean())
              << req.dump() << " -> " << out;
          ++requests;
        }
      }
    }
  }
  EXPECT_EQ(requests, 9 * 6 * 11 * 4);
  EXPECT_EQ(call(svc, R"({"cmd":"hello"})")["ok"], true) << "and the protocol still answers";
}
// [/snippet:type_confusion]

// [snippet:status_fields_test]
TEST(ControlProtocol, StatusFieldsMatchTheApiVersion) {
  // REQ: SRS-CTL-033
  ServiceOptions o = with_default_adapters();
  o.interval_period = 30ms;
  AcquisitionService svc{o};
  std::set<std::string> seen;
  const auto check = [&](const json& status, const char* when) {
    for (const auto& [name, value] : status.items()) {
      seen.insert(name);
      EXPECT_TRUE(std::any_of(status_fields.begin(), status_fields.end(), [&](const StatusField& f) { return f.name == name; }))
          << when << ": field '" << name << "' is not in status_fields of API " << api_version;
    }
    for (const auto& f : status_fields) {
      if (f.always) {
        EXPECT_TRUE(status.contains(std::string{f.name})) << when << ": no field '" << f.name << "'";
      }
    }
  };
  check(call(svc, R"({"cmd":"status"})")["status"], "idle");
  ASSERT_EQ(call(svc, R"({"cmd":"configure","config":{"schema_version":"1.0","source":{"rate_hz":1e6}}})")["ok"], true);
  check(call(svc, R"({"cmd":"status"})")["status"], "configured");
  ASSERT_EQ(call(svc, R"({"cmd":"start"})")["ok"], true);
  json running;
  ASSERT_TRUE(test_support::eventually([&] {
    running = call(svc, R"({"cmd":"status"})")["status"];
    return running.contains("recent_latency_ns");
  }));
  check(running, "running");
  ASSERT_EQ(call(svc, R"({"cmd":"stop"})")["ok"], true);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
  check(call(svc, R"({"cmd":"status"})")["status"], "after the run");
  for (const auto& f : status_fields) {
    EXPECT_TRUE(seen.contains(std::string{f.name})) << "status_fields lists '" << f.name << "', which never appeared";
  }
  EXPECT_EQ(call(svc, R"({"cmd":"hello"})")["api"], "2.3");
}
// [/snippet:status_fields_test]

TEST(ControlProtocol, DiagnosticsReturnTheNewestEventsOfTheFlightRecorder) {
  // REQ: SRS-DIAG-003, SRS-DIAG-004
  AcquisitionService svc{with_default_adapters()};
  ASSERT_EQ(call(svc, R"({"cmd":"configure","config":{"schema_version":"1.0","stop_after_s":0.01}})")["ok"], true);
  ASSERT_EQ(call(svc, R"({"cmd":"start"})")["ok"], true);
  ASSERT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
  const json r = call(svc, R"({"cmd":"diagnostics","events":1024})");
  ASSERT_EQ(r["ok"], true) << r.dump();
  const json& d = r["diagnostics"];
  EXPECT_NE(d["server"].get<std::string>().find("minidaq"), std::string::npos);
  EXPECT_FALSE(d["build_id"].get<std::string>().empty());
  EXPECT_GE(d["recorder"]["recorded"].get<std::uint64_t>(), d["events"].size());
  // This run, as the recorder saw it: the commands, the state changes, the run's begin and end.
  std::vector<std::string> seen;
  for (const auto& e : d["events"]) {
    seen.push_back(e["code"].get<std::string>() + " " + e["a"].dump() + " " + e["b"].dump());
  }
  const auto has = [&](const std::string& what) { return std::ranges::find(seen, what) != seen.end(); };
  const auto st = [](AcqState x) { return std::to_string(static_cast<int>(x)); };
  EXPECT_TRUE(has("command " + std::to_string(static_cast<int>(CommandId::configure)) + " 1"));
  EXPECT_TRUE(has("command " + std::to_string(static_cast<int>(CommandId::start)) + " 1"));
  EXPECT_TRUE(has("state " + st(AcqState::idle) + " " + st(AcqState::configured)));
  EXPECT_TRUE(has("state " + st(AcqState::configured) + " " + st(AcqState::running)));
  const std::uint64_t run = call(svc, R"({"cmd":"status"})")["status"]["run_id"].get<std::uint64_t>();
  EXPECT_TRUE(has("run_begin " + std::to_string(run) + " 0"));
  EXPECT_TRUE(has("run_end " + std::to_string(run) + " 1")) << "complete";
  // Oldest first, and only as many as asked.
  for (std::size_t i = 1; i < d["events"].size(); ++i) {
    EXPECT_LE(d["events"][i - 1]["t_ns"], d["events"][i]["t_ns"]);
  }
  EXPECT_EQ(call(svc, R"({"cmd":"diagnostics","events":2})")["diagnostics"]["events"].size(), 2U);
  // The count before the call: the command is traced after its snapshot, and the two operands
  // of EXPECT_EQ may be evaluated in either order (Clang and GCC differ here).
  const std::uint64_t before = flight_recorder().counts().recorded;
  EXPECT_EQ(call(svc, R"({"cmd":"diagnostics"})")["diagnostics"]["events"].size(),
            std::min<std::size_t>(diagnostics_default_events, before));
  for (const char* bad : {R"({"cmd":"diagnostics","events":1025})", R"({"cmd":"diagnostics","events":-1})",
                          R"({"cmd":"diagnostics","events":"5"})", R"({"cmd":"diagnostics","events":1.5})"}) {
    EXPECT_EQ(call(svc, bad)["error"]["code"], "bad_request") << bad;
  }
}

namespace {

using test_support::Client;

// A server whose one operator token the tests know.
struct Secured {
  std::string token = new_token();
  ServerSecurity security{std::make_shared<const TokenStore>(TokenStore::single("test", Role::operator_, token)), nullptr};
};

}  // namespace

TEST(ControlServer, PipelinedRequestsAndManyClients) {
  AcquisitionService svc{with_default_adapters()};
  const Secured sec;
  ControlServer server{svc, 0, sec.security};
  const auto port = server.start();
  ASSERT_TRUE(port) << port.error();
  Client a{*port};
  Client b{*port};
  ASSERT_TRUE(a.ok() && b.ok());
  ASSERT_TRUE(a.auth(sec.token) && b.auth(sec.token));
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
  const Secured sec;
  ControlServer server{svc, 0, sec.security};
  const auto port = server.start();
  ASSERT_TRUE(port);
  {
    Client c{*port};
    ASSERT_TRUE(c.auth(sec.token));
    ASSERT_EQ(c.call({{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}, {"source", {{"rate_hz", 1e6}}}}}})["ok"],
              true);
    ASSERT_EQ(c.call({{"cmd", "start"}})["state"], "running");
  }  // the client goes away mid-run
  std::this_thread::sleep_for(50ms);  // sleep: hides only (gives a wrong stop the time to happen)
  EXPECT_EQ(svc.state(), AcqState::running);
  Client again{*port};
  ASSERT_TRUE(again.auth(sec.token));
  const auto st = again.call({{"cmd", "status"}});
  EXPECT_EQ(st["status"]["state"], "running");
  EXPECT_EQ(st["status"]["run_id"], 1) << "a new client sees the same run";
  EXPECT_EQ(again.call({{"cmd", "stop"}})["ok"], true);
  EXPECT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
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
  const Secured sec;
  ControlServer server{svc, 0, sec.security};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client c{*port};
  ASSERT_TRUE(c.ok());
  ASSERT_TRUE(c.auth(sec.token));
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
    EXPECT_TRUE(r.who.starts_with("test@tcp:127.0.0.1:")) << r.action << " by " << r.who << ": identity and address";
    seen.emplace_back(r.action, r.ok);
  }
  const std::vector<std::pair<std::string, bool>> expected{
      {"start", false}, {"configure", true}, {"configure", false}, {"reset", true}};
  EXPECT_EQ(seen, expected);
}

TEST(ControlServer, OverlongRequestClosesOnlyThatConnection) {
  // REQ: SRS-CTL-021
  AcquisitionService svc{with_default_adapters()};
  const Secured sec;
  ControlServer server{svc, 0, sec.security};
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
  const Secured sec;
  ControlServer server{svc, 0, sec.security, "127.0.0.1", 2};
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
  const Secured sec;
  ControlServer server{svc, 0, sec.security, "not-an-address"};
  const auto r = server.start();
  ASSERT_FALSE(r);
  EXPECT_NE(r.error().find("bad bind address"), std::string::npos);
}
