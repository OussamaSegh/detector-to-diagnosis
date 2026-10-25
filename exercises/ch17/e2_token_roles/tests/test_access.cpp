// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <map>
#include <string>

#include "access.hpp"

using ex172::Identity;
using ex172::required_role;
using ex172::Role;
using ex172::TokenStore;

namespace {

std::string hex64(char c) { return std::string(64, c); }
std::string token(char c) { return "mdq_" + hex64(c); }

// A stand-in for SHA-256: the digest of token(c) is hex64(c) with its first digit
// changed to 'f', so a digest is never the token's own hex.
std::string fake_digest(std::string_view t) {
  std::string d{t.substr(t.size() >= 64 ? t.size() - 64 : 0)};
  if (!d.empty()) {
    d[0] = 'f';
  }
  return d;
}

struct Counter {
  int calls = 0;
  ex172::Equal equal() {
    return [this](std::string_view a, std::string_view b) {
      ++calls;
      return a == b;
    };
  }
};

std::string line(const std::string& name, const std::string& role, char c) {
  return name + " " + role + " " + fake_digest(token(c)) + "\n";
}

}  // namespace

TEST(Roles, UnknownCommandsNeedTheOperator) {
  EXPECT_EQ(required_role("hello"), Role::none);
  EXPECT_EQ(required_role("auth"), Role::none);
  EXPECT_EQ(required_role("status"), Role::observer);
  for (const char* cmd : {"configure", "start", "stop", "reset"}) {
    EXPECT_EQ(required_role(cmd), Role::operator_) << cmd;
  }
  for (const char* cmd : {"calibrate", "shutdown", "", "STATUS", "status "}) {
    EXPECT_EQ(required_role(cmd), Role::operator_) << "'" << cmd << "' fails closed";
  }
}

TEST(TokenStore, FindsEachToken) {
  Counter n;
  auto s = TokenStore::parse("# console and dashboard\n" + line("console", "operator", 'a') + "\n" +
                                 line("dashboard", "observer", 'b'),
                             fake_digest, n.equal());
  ASSERT_TRUE(s) << s.error();
  EXPECT_EQ(s->size(), 2U);
  const auto op = s->check(token('a'));
  ASSERT_TRUE(op);
  EXPECT_EQ(op->name, "console");
  EXPECT_EQ(op->role, Role::operator_);
  const auto obs = s->check(token('b'));
  ASSERT_TRUE(obs);
  EXPECT_EQ(obs->role, Role::observer);
  EXPECT_FALSE(s->check(token('c')));
}

TEST(TokenStore, RefusesBadFiles) {
  Counter n;
  auto bad = [&](const std::string& text) { return !TokenStore::parse(text, fake_digest, n.equal()); };
  EXPECT_TRUE(bad("")) << "no tokens";
  EXPECT_TRUE(bad("# only a comment\n")) << "no tokens";
  EXPECT_TRUE(bad(line("x", "admin", 'a'))) << "unknown role";
  EXPECT_TRUE(bad(line("x", "Operator", 'a'))) << "roles are exact";
  EXPECT_TRUE(bad("x operator " + hex64('A') + "\n")) << "uppercase hex";
  EXPECT_TRUE(bad("x operator " + hex64('a').substr(1) + "\n")) << "63 digits";
  EXPECT_TRUE(bad("x operator " + hex64('g') + "\n")) << "not hex";
  EXPECT_TRUE(bad("x operator " + hex64('a') + " extra\n")) << "extra field";
  EXPECT_TRUE(bad("x operator\n")) << "no digest";
  EXPECT_TRUE(bad(line("x", "operator", 'a') + line("x", "observer", 'b'))) << "name used twice";
  EXPECT_TRUE(bad(line("x", "operator", 'a') + line("y", "observer", 'a'))) << "digest used twice";
  const auto e = TokenStore::parse(line("x", "operator", 'a') + line("y", "admin", 'b'), fake_digest, n.equal());
  ASSERT_FALSE(e);
  EXPECT_NE(e.error().find("line 2"), std::string::npos) << e.error();
}

TEST(TokenStore, ComparesWithEveryEntry) {
  Counter n;
  auto s = TokenStore::parse(line("a", "operator", 'a') + line("b", "observer", 'b') + line("c", "observer", 'c'),
                             fake_digest, n.equal());
  ASSERT_TRUE(s);
  for (char c : {'a', 'b', 'c', 'd'}) {
    n.calls = 0;
    (void)s->check(token(c));
    EXPECT_EQ(n.calls, 3) << "token " << c << ": the constant-time comparison is used for every entry";
  }
}

TEST(TokenStore, RefusesWhatIsNotAToken) {
  Counter n;
  // An entry whose digest is that of a malformed "token": still never accepted.
  auto s = TokenStore::parse("odd operator " + fake_digest("x" + hex64('e')) + "\n" + line("a", "operator", 'a'),
                             fake_digest, n.equal());
  ASSERT_TRUE(s) << s.error();
  n.calls = 0;
  for (const std::string& t : {std::string{}, "x" + hex64('e'), "mdq_" + hex64('a').substr(1), "MDQ_" + hex64('a'),
                               "mdq_" + hex64('a') + "\n", " mdq_" + hex64('a')}) {
    EXPECT_FALSE(s->check(t)) << "'" << t << "'";
  }
  EXPECT_EQ(n.calls, 0) << "malformed input is refused before it is hashed or compared";
}
