// SPDX-License-Identifier: MIT
// Chapter 17: authentication, authorization and TLS of the control API.
#include <gtest/gtest.h>

#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <poll.h>
#include <sys/stat.h>
#include <unistd.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>
#include <thread>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/access.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/control/control_protocol.hpp"
#include "minidaq/control/control_server.hpp"
#include "minidaq/control/tls.hpp"
#include "eventually.hpp"
#include "test_client.hpp"
#include "test_pki.hpp"

using namespace minidaq;
using namespace minidaq::control;
using nlohmann::json;
using test_support::Client;
using namespace std::chrono_literals;

namespace {

// A fresh directory under the system's temporary directory, removed afterwards.
class TempDir {
 public:
  TempDir() {
    std::string tmpl = (std::filesystem::temp_directory_path() / "minidaq-sec-XXXXXX").string();
    path_ = ::mkdtemp(tmpl.data());
  }
  ~TempDir() {
    std::error_code ignored;
    std::filesystem::remove_all(path_, ignored);
  }
  TempDir(const TempDir&) = delete;
  TempDir& operator=(const TempDir&) = delete;
  [[nodiscard]] const std::filesystem::path& path() const { return path_; }

 private:
  std::filesystem::path path_;
};

// An audit sink that keeps the records.
struct Audit {
  std::mutex mu;
  std::vector<AuditRecord> records;
  ServiceOptions options() {
    ServiceOptions o = with_default_adapters();
    o.audit = [this](const AuditRecord& r) {
      const std::lock_guard lock{mu};
      records.push_back(r);
    };
    return o;
  }
  bool has(const std::string& action, const std::string& detail_part, bool ok) {
    const std::lock_guard lock{mu};
    for (const auto& r : records) {
      if (r.action == action && r.detail.find(detail_part) != std::string::npos && r.ok == ok) {
        return true;
      }
    }
    return false;
  }
};

// One operator and one observer token.
struct Tokens {
  std::string op = new_token();
  std::string obs = new_token();
  std::shared_ptr<const TokenStore> store;
  explicit Tokens(const std::filesystem::path& dir) {
    const auto file = dir / "tokens.json";
    std::ofstream{file} << json{{"tokens",
                                 {{{"name", "console"}, {"role", "operator"}, {"sha256", token_sha256_hex(op)}},
                                  {{"name", "dashboard"}, {"role", "observer"}, {"sha256", token_sha256_hex(obs)}}}}}
                               .dump();
    ::chmod(file.c_str(), 0600);
    auto s = TokenStore::load(file);
    EXPECT_TRUE(s) << s.error();
    store = std::make_shared<const TokenStore>(std::move(*s));
  }
};

const json configure{{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}}}};

}  // namespace

TEST(TokenStore, LoadsHashesAndRefusesUnsafeFiles) {
  // REQ: SRS-SEC-008
  const TempDir dir;
  const Tokens t{dir.path()};
  EXPECT_EQ(t.store->size(), 2U);
  const auto op = t.store->check(t.op);
  ASSERT_TRUE(op);
  EXPECT_EQ(op->name, "console");
  EXPECT_EQ(op->role, Role::operator_);
  EXPECT_EQ(t.store->check(t.obs)->role, Role::observer);
  EXPECT_FALSE(t.store->check(""));
  EXPECT_FALSE(t.store->check(t.op + "x"));
  EXPECT_FALSE(t.store->check(token_sha256_hex(t.op))) << "the stored hash is not a token";
  std::string text;
  std::getline(std::ifstream{dir.path() / "tokens.json"}, text, '\0');
  EXPECT_EQ(text.find(t.op), std::string::npos) << "the file holds hashes only";

  const auto file = dir.path() / "tokens.json";
  ::chmod(file.c_str(), 0620);
  const auto writable = TokenStore::load(file);
  ASSERT_FALSE(writable);
  EXPECT_NE(writable.error().find("accessible to other users"), std::string::npos) << writable.error();
  ::chmod(file.c_str(), 0644);
  EXPECT_TRUE(TokenStore::load(file)) << "others may read hashes, not write them";

  const auto link = dir.path() / "link.json";
  std::filesystem::create_symlink(file, link);
  EXPECT_FALSE(TokenStore::load(link)) << "a symbolic link could point anywhere";

  const auto bad = dir.path() / "bad.json";
  for (const char* doc : {R"({"tokens": []})", R"({"tokens": [{"name": "a", "role": "admin", "sha256": "00"}]})",
                          R"({"tokens": [{"name": "a", "role": "operator", "sha256": "xyz"}]})", R"([1])"}) {
    std::ofstream{bad} << doc;
    ::chmod(bad.c_str(), 0600);
    EXPECT_FALSE(TokenStore::load(bad)) << doc;
  }
  const std::string h = token_sha256_hex(t.op);
  std::ofstream{bad} << json{{"tokens",
                              {{{"name", "a"}, {"role", "operator"}, {"sha256", h}},
                               {{"name", "b"}, {"role", "observer"}, {"sha256", h}}}}}
                            .dump();
  EXPECT_FALSE(TokenStore::load(bad)) << "one token, two roles";
}

TEST(Secrets, StartupTokenIsPrivate) {
  // REQ: SRS-SEC-009
  const std::string a = new_token();
  const std::string b = new_token();
  ASSERT_EQ(a.size(), 4U + 64U);
  EXPECT_TRUE(a.starts_with("mdq_")) << "a prefix lets secret scanners find leaked tokens";
  EXPECT_NE(a, b);

  const TempDir dir;
  const auto file = dir.path() / "run" / "minidaq-7700.token";
  const auto written = write_secret(file, a);
  ASSERT_TRUE(written) << written.error();
  struct stat st{};
  ASSERT_EQ(::stat(file.parent_path().c_str(), &st), 0);
  EXPECT_EQ(st.st_mode & 0777U, 0700U);
  ASSERT_EQ(::stat(file.c_str(), &st), 0);
  EXPECT_EQ(st.st_mode & 0777U, 0600U);
  EXPECT_EQ(*read_secret(file), a);
  EXPECT_TRUE(write_secret(file, b)) << "a file left by a crashed server is replaced";
  EXPECT_EQ(*read_secret(file), b);

  ::chmod(file.c_str(), 0640);
  EXPECT_FALSE(read_secret(file)) << "a token that others can read may already be theirs";
  ::chmod(file.parent_path().c_str(), 0755);
  EXPECT_FALSE(write_secret(file, a)) << "a directory others can enter is not private";

  const auto real = dir.path() / "real";
  std::filesystem::create_directory(real);
  ::chmod(real.c_str(), 0700);
  std::filesystem::create_directory_symlink(real, dir.path() / "linked");
  EXPECT_FALSE(write_secret(dir.path() / "linked" / "t.token", a)) << "a link in /tmp may be someone else's";

  ::setenv("MINIDAQ_RUNTIME_DIR", "/run/x", 1);
  EXPECT_EQ(default_token_path(7700), "/run/x/minidaq-7700.token");
  ::unsetenv("MINIDAQ_RUNTIME_DIR");
}

TEST(ControlServer, CommandsNeedAnAuthenticatedClient) {
  // REQ: SRS-SEC-001
  const TempDir dir;
  const Tokens t{dir.path()};
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0, ServerSecurity{t.store, nullptr}};
  const auto port = server.start();
  ASSERT_TRUE(port) << port.error();
  Client c{*port};
  const auto hello = c.call({{"cmd", "hello"}});
  EXPECT_EQ(hello["ok"], true) << "hello tells a client what to do next";
  EXPECT_EQ(hello["auth"], "token");
  for (const char* cmd : {"status", "start", "stop", "reset"}) {
    EXPECT_EQ(c.call({{"cmd", cmd}})["error"]["code"], "unauthenticated") << cmd;
  }
  EXPECT_EQ(c.call(configure)["error"]["code"], "unauthenticated");
  EXPECT_EQ(svc.state(), AcqState::idle);
  const auto r = c.call({{"cmd", "auth"}, {"token", t.op}});
  EXPECT_EQ(r["ok"], true);
  EXPECT_EQ(r["identity"], "console");
  EXPECT_EQ(r["role"], "operator");
  EXPECT_EQ(c.call(configure)["ok"], true);
  EXPECT_EQ(svc.state(), AcqState::configured);
}

TEST(ControlServer, AnUnknownTokenClosesTheConnection) {
  // REQ: SRS-SEC-002
  const TempDir dir;
  const Tokens t{dir.path()};
  Audit audit;
  AcquisitionService svc{audit.options()};
  ControlServer server{svc, 0, ServerSecurity{t.store, nullptr}};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client c{*port};
  const std::string guess = t.op.substr(0, t.op.size() - 1) + (t.op.back() == '0' ? "1" : "0");
  const auto r = c.call({{"cmd", "auth"}, {"token", guess}});
  EXPECT_EQ(r["error"]["code"], "unauthenticated");
  EXPECT_EQ(c.line(), "") << "no second guess on the same connection";
  EXPECT_TRUE(audit.has("auth", "refused", false));
  Client c2{*port};  // MDQ-PR-013: a token that is not a string once ended the server
  EXPECT_EQ(c2.call({{"cmd", "auth"}, {"token", 5}})["error"]["code"], "unauthenticated");
  Client c3{*port};
  EXPECT_EQ(c3.call({{"cmd", "hello"}})["ok"], true) << "the server still answers";
  const std::lock_guard lock{audit.mu};
  for (const auto& rec : audit.records) {
    EXPECT_EQ(rec.detail.find("mdq_"), std::string::npos) << "a token in the audit trail: " << rec.detail;
    if (rec.action == "auth") {
      EXPECT_TRUE(rec.who.starts_with("tcp:127.0.0.1:")) << rec.who;
    }
  }
}

TEST(ControlServer, ObserversMayOnlyReadTheStatus) {
  // REQ: SRS-SEC-003
  const TempDir dir;
  const Tokens t{dir.path()};
  Audit audit;
  AcquisitionService svc{audit.options()};
  ControlServer server{svc, 0, ServerSecurity{t.store, nullptr}};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client c{*port};
  ASSERT_TRUE(c.auth(t.obs));
  EXPECT_EQ(c.call({{"cmd", "status"}})["status"]["state"], "idle");
  EXPECT_EQ(c.call({{"cmd", "diagnostics"}})["ok"], true) << "API 2.1: diagnostics only reads";
  const auto r = c.call(configure);
  EXPECT_EQ(r["error"]["code"], "forbidden");
  EXPECT_NE(r["error"]["message"].get<std::string>().find("operator"), std::string::npos);
  for (const char* cmd : {"start", "stop", "reset"}) {
    EXPECT_EQ(c.call({{"cmd", cmd}})["error"]["code"], "forbidden") << cmd;
  }
  EXPECT_EQ(svc.state(), AcqState::idle);
  EXPECT_TRUE(audit.has("configure", "refused: role", false));
  EXPECT_EQ(c.call({{"cmd", "status"}})["ok"], true) << "a refusal does not end the session";
}

TEST(ControlServer, ClosesConnectionsThatDoNotAuthenticate) {
  // REQ: SRS-SEC-004
  const TempDir dir;
  const Tokens t{dir.path()};
  Audit audit;
  AcquisitionService svc{audit.options()};
  ServerSecurity sec{t.store, nullptr};
  sec.auth_deadline = 200ms;
  ControlServer server{svc, 0, sec, "127.0.0.1", 2};
  const auto port = server.start();
  ASSERT_TRUE(port);
  {
    Client idle1{*port};
    Client idle2{*port};
    ASSERT_TRUE(test_support::eventually([&] { return server.clients() == 2; }));
    EXPECT_EQ(idle1.line(), "") << "closed without a word";
    ASSERT_TRUE(test_support::eventually([&] { return server.clients() == 0; }))
        << "silent clients no longer hold the slots";
  }
  EXPECT_TRUE(audit.has("disconnect", "not authenticated in time", false));
  Client c{*port};
  ASSERT_TRUE(c.auth(t.op));
  std::this_thread::sleep_for(400ms);  // sleep: minimum (past the deadline, which no longer applies)
  EXPECT_EQ(c.call({{"cmd", "status"}})["ok"], true) << "an authenticated session has no deadline";
}

TEST(ControlServer, RefusesInsecureConfigurations) {
  // REQ: SRS-SEC-005
  const TempDir dir;
  const Tokens t{dir.path()};
  const auto pki = test_support::make_pki(dir.path());
  auto tls = TlsContext::server(pki.server_cert, pki.server_key);
  ASSERT_TRUE(tls) << tls.error();
  const auto ctx = std::make_shared<const TlsContext>(std::move(*tls));
  AcquisitionService svc{with_default_adapters()};

  ControlServer none{svc, 0, ServerSecurity{}};
  const auto r1 = none.start();
  ASSERT_FALSE(r1);
  EXPECT_NE(r1.error().find("no tokens"), std::string::npos) << r1.error();

  ServerSecurity open;
  open.allow_unauthenticated = true;
  ControlServer bench{svc, 0, open};
  EXPECT_TRUE(bench.start()) << "a test bench may turn authentication off, on loopback";
  bench.stop();
  ControlServer exposed{svc, 0, open, "0.0.0.0"};
  EXPECT_FALSE(exposed.start());
  ControlServer plain{svc, 0, ServerSecurity{t.store, nullptr}, "0.0.0.0"};
  const auto r2 = plain.start();
  ASSERT_FALSE(r2);
  EXPECT_NE(r2.error().find("needs TLS and tokens"), std::string::npos) << r2.error();
  ControlServer unauthenticated{svc, 0, ServerSecurity{nullptr, ctx, true}, "0.0.0.0"};
  EXPECT_FALSE(unauthenticated.start()) << "TLS without tokens encrypts an open door";
  ControlServer secured{svc, 0, ServerSecurity{t.store, ctx}, "0.0.0.0"};
  EXPECT_TRUE(secured.start()) << "TLS and tokens may face the network";
}

TEST(ControlServer, ServesOnlyTls13Clients) {
  // REQ: SRS-SEC-006
  const TempDir dir;
  const Tokens t{dir.path()};
  const auto pki = test_support::make_pki(dir.path());
  auto tls = TlsContext::server(pki.server_cert, pki.server_key);
  ASSERT_TRUE(tls) << tls.error();
  Audit audit;
  AcquisitionService svc{audit.options()};
  ControlServer server{svc, 0, ServerSecurity{t.store, std::make_shared<const TlsContext>(std::move(*tls))}};
  const auto port = server.start();
  ASSERT_TRUE(port);

  auto client_ctx = TlsContext::client(pki.ca_cert);
  ASSERT_TRUE(client_ctx) << client_ctx.error();
  Client c{*port, &*client_ctx};
  ASSERT_TRUE(c.ok()) << c.error();
  ASSERT_TRUE(c.auth(t.op));
  EXPECT_EQ(c.call(configure)["ok"], true);
  // Three requests in one TLS record: three responses, in order.
  c.send("{\"id\":1,\"cmd\":\"hello\"}\n{\"id\":2,\"cmd\":\"status\"}\n{\"id\":3,\"cmd\":\"reset\"}\n");
  EXPECT_EQ(json::parse(c.line())["id"], 1);
  EXPECT_EQ(json::parse(c.line())["id"], 2);
  EXPECT_EQ(json::parse(c.line())["id"], 3);

  Client plain{*port};
  plain.send("{\"cmd\":\"hello\"}\n");
  EXPECT_EQ(plain.line(), "") << "no answer in plain text";
  EXPECT_TRUE(audit.has("disconnect", "TLS handshake failed", false));

  // A TLS 1.2 client is refused during the handshake.
  SSL_CTX* old = SSL_CTX_new(TLS_client_method());
  ASSERT_NE(old, nullptr);
  SSL_CTX_set_max_proto_version(old, TLS1_2_VERSION);
  SSL_CTX_set_verify(old, SSL_VERIFY_NONE, nullptr);
  const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons(*port);
  ::inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
  ASSERT_EQ(::connect(fd, reinterpret_cast<const sockaddr*>(&a), sizeof a), 0);
  SSL* ssl = SSL_new(old);
  SSL_set_fd(ssl, fd);
  EXPECT_NE(SSL_connect(ssl), 1) << "TLS 1.2 is not offered";
  SSL_free(ssl);
  SSL_CTX_free(old);
  ::close(fd);
}

TEST(TlsStream, ClientVerifiesTheServer) {
  // REQ: SRS-SEC-007
  const TempDir dir;
  const Tokens t{dir.path()};
  const auto pki = test_support::make_pki(dir.path());
  auto tls = TlsContext::server(pki.server_cert, pki.server_key);
  ASSERT_TRUE(tls);
  Audit audit;
  AcquisitionService svc{audit.options()};
  ControlServer server{svc, 0, ServerSecurity{t.store, std::make_shared<const TlsContext>(std::move(*tls))}};
  const auto port = server.start();
  ASSERT_TRUE(port);

  auto trusted = TlsContext::client(pki.ca_cert);
  ASSERT_TRUE(trusted);
  EXPECT_TRUE(Client(*port, &*trusted, "localhost").ok()) << "the certificate names localhost too";
  Client wrong_name{*port, &*trusted, "daq.example.org"};
  EXPECT_FALSE(wrong_name.ok());
  EXPECT_NE(wrong_name.error().find("certificate"), std::string::npos) << wrong_name.error();

  auto stranger = TlsContext::client(pki.other_ca_cert);
  ASSERT_TRUE(stranger);
  Client impostor_check{*port, &*stranger};
  EXPECT_FALSE(impostor_check.ok()) << "a server that another CA vouches for is not ours";
  EXPECT_FALSE(audit.has("auth", "", true)) << "no token was sent to a server that failed verification";

  EXPECT_FALSE(TlsContext::server(pki.server_cert, pki.ca_cert)) << "a key that does not match the certificate";
  EXPECT_FALSE(TlsContext::client((dir.path() / "missing.pem").string()));
}

TEST(ControlProtocol, AuthenticationInTheProtocolLayer) {
  // REQ: SRS-SEC-001
  AcquisitionService svc{with_default_adapters()};
  const std::string token = new_token();
  const TokenStore tokens = TokenStore::single("console", Role::operator_, token);
  Session s{"tcp:192.0.2.7:4000", {}};
  auto call_as = [&](Session& session, const json& req) {
    return json::parse(handle_request(req.dump(), svc, session, &tokens));
  };
  auto call = [&](const json& req) { return call_as(s, req); };
  EXPECT_EQ(call({{"cmd", "status"}})["error"]["code"], "unauthenticated");
  EXPECT_EQ(s.who(), "tcp:192.0.2.7:4000");
  EXPECT_EQ(call({{"cmd", "auth"}})["error"]["code"], "unauthenticated") << "no token is an unknown token";
  EXPECT_TRUE(s.failed_auth);
  // MDQ-PR-013: a token that is not a string threw out of handle_request and ended the server.
  for (const json& bad : {json(5), json(nullptr), json::array({token}), json{{"token", token}}, json(true)}) {
    Session sb{"tcp:192.0.2.7:4002", {}};
    EXPECT_EQ(call_as(sb, {{"cmd", "auth"}, {"token", bad}})["error"]["code"], "unauthenticated") << bad.dump();
    EXPECT_TRUE(sb.failed_auth) << bad.dump();
  }
  Session s2{"tcp:192.0.2.7:4001", {}};
  EXPECT_EQ(json::parse(handle_request(json{{"cmd", "auth"}, {"token", token}}.dump(), svc, s2, &tokens))["ok"], true);
  EXPECT_EQ(s2.who(), "console@tcp:192.0.2.7:4001");
  EXPECT_EQ(required_role("launch"), Role::operator_) << "a command added later needs an operator until decided";
  EXPECT_EQ(required_role("diagnostics"), Role::observer) << "API 2.1, ADR 0016: it reads, like status";
}

// [snippet:effectiveness]
TEST(ControlServer, AnIntruderCannotStopARunningScan) {
  // REQ: SRS-SEC-001, SRS-SEC-003
  // Effectiveness of RC-21 and RC-22 (hazard H-08): the sequence of events of the
  // hazard, a local process that connects and sends stop or configure, no longer
  // reaches the acquisition, whatever it knows short of an operator token.
  const TempDir dir;
  const Tokens t{dir.path()};
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0, ServerSecurity{t.store, nullptr}};
  const auto port = server.start();
  ASSERT_TRUE(port);
  Client console{*port};
  ASSERT_TRUE(console.auth(t.op));
  ASSERT_EQ(console.call({{"cmd", "configure"}, {"config", {{"schema_version", "1.0"}, {"source", {{"rate_hz", 1e6}}}}}})["ok"],
            true);
  ASSERT_EQ(console.call({{"cmd", "start"}})["state"], "running");

  const json attacks[] = {{{"cmd", "stop"}},
                          {{"cmd", "reset"}},
                          {{"api", "1.1"}, {"cmd", "stop"}},
                          {{"cmd", "auth"}, {"token", ""}},
                          {{"cmd", "auth"}, {"token", t.obs + "\n{\"cmd\":\"stop\"}"}},
                          {{"cmd", "auth"}, {"token", token_sha256_hex(t.op)}}};
  for (const auto& attack : attacks) {
    Client intruder{*port};
    (void)intruder.call(attack);
    (void)intruder.call({{"cmd", "stop"}});
  }
  Client observer{*port};
  ASSERT_TRUE(observer.auth(t.obs));
  EXPECT_EQ(observer.call({{"cmd", "stop"}})["error"]["code"], "forbidden");
  EXPECT_EQ(observer.call(configure)["error"]["code"], "forbidden");
  EXPECT_EQ(svc.state(), AcqState::running) << "the scan goes on";
  EXPECT_EQ(console.call({{"cmd", "stop"}})["ok"], true) << "the operator still can";
  EXPECT_TRUE(svc.wait_for(AcqState::configured, test_support::patience));
}
// [/snippet:effectiveness]

namespace {

// Copies bytes between a client and a server in both directions and keeps a
// copy of everything, as an eavesdropper on the network would.
class Relay {
 public:
  explicit Relay(std::uint16_t server_port) : server_port_{server_port} {
    listen_ = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    ::inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    ::bind(listen_, reinterpret_cast<const sockaddr*>(&a), sizeof a);
    ::listen(listen_, 1);
    socklen_t len = sizeof a;
    ::getsockname(listen_, reinterpret_cast<sockaddr*>(&a), &len);
    port_ = ntohs(a.sin_port);
    thread_ = std::jthread{[this](const std::stop_token& st) { run(st); }};
  }
  ~Relay() {
    thread_.request_stop();
    thread_.join();
    ::close(listen_);
  }
  Relay(const Relay&) = delete;
  Relay& operator=(const Relay&) = delete;
  [[nodiscard]] std::uint16_t port() const { return port_; }
  [[nodiscard]] std::string seen() {
    const std::lock_guard lock{mu_};
    return seen_;
  }

 private:
  void run(const std::stop_token& st) {
    const int c = ::accept(listen_, nullptr, nullptr);
    const int s = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(server_port_);
    ::inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    ::connect(s, reinterpret_cast<const sockaddr*>(&a), sizeof a);
    while (!st.stop_requested()) {
      pollfd fds[2] = {{c, POLLIN, 0}, {s, POLLIN, 0}};
      if (::poll(fds, 2, 50) <= 0) {
        continue;
      }
      for (int i = 0; i < 2; ++i) {
        if ((fds[i].revents & (POLLIN | POLLHUP)) == 0) {
          continue;
        }
        char buf[4096];
        const ssize_t n = ::recv(fds[i].fd, buf, sizeof buf, 0);
        if (n <= 0) {
          ::close(c);
          ::close(s);
          return;
        }
        {
          const std::lock_guard lock{mu_};
          seen_.append(buf, static_cast<std::size_t>(n));
        }
        (void)::send(i == 0 ? s : c, buf, static_cast<std::size_t>(n), MSG_NOSIGNAL);
      }
    }
    ::close(c);
    ::close(s);
  }

  std::uint16_t server_port_;
  std::uint16_t port_ = 0;
  int listen_ = -1;
  std::mutex mu_;
  std::string seen_;
  std::jthread thread_;
};

}  // namespace

TEST(ControlServer, TheTokenNeverCrossesTheNetworkInClear) {
  // REQ: SRS-SEC-006
  // Effectiveness of RC-23 (hazard H-08): an eavesdropper between client and
  // server sees neither the token nor the commands, and cannot become the server.
  const TempDir dir;
  const Tokens t{dir.path()};
  const auto pki = test_support::make_pki(dir.path());
  auto tls = TlsContext::server(pki.server_cert, pki.server_key);
  ASSERT_TRUE(tls);
  AcquisitionService svc{with_default_adapters()};
  ControlServer server{svc, 0, ServerSecurity{t.store, std::make_shared<const TlsContext>(std::move(*tls))}};
  const auto port = server.start();
  ASSERT_TRUE(port);
  auto ctx = TlsContext::client(pki.ca_cert);
  ASSERT_TRUE(ctx);
  {
    Relay relay{*port};
    Client c{relay.port(), &*ctx};
    ASSERT_TRUE(c.ok()) << c.error();
    ASSERT_TRUE(c.auth(t.op));
    ASSERT_EQ(c.call(configure)["ok"], true);
    const std::string wire = relay.seen();
    EXPECT_GT(wire.size(), 500U) << "the handshake and the requests went through the relay";
    EXPECT_EQ(wire.find(t.op), std::string::npos) << "the token in clear on the wire";
    EXPECT_EQ(wire.find("configure"), std::string::npos) << "a command in clear on the wire";
    EXPECT_EQ(wire.find(t.op.substr(4, 16)), std::string::npos);
  }
  // Without TLS, the same eavesdropper reads the token: why RC-23 exists.
  ControlServer plain{svc, 0, ServerSecurity{t.store, nullptr}};
  const auto plain_port = plain.start();
  ASSERT_TRUE(plain_port);
  Relay relay{*plain_port};
  Client c{relay.port()};
  ASSERT_TRUE(c.auth(t.op));
  EXPECT_NE(relay.seen().find(t.op), std::string::npos);
}
