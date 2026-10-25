// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include "bind_check.hpp"

using ex175::check_bind;
using ex175::is_loopback;
using ex175::Security;

TEST(Loopback, Ipv4) {
  EXPECT_TRUE(is_loopback("127.0.0.1"));
  EXPECT_TRUE(is_loopback("127.1.2.3")) << "all of 127.0.0.0/8";
  EXPECT_TRUE(is_loopback("127.255.255.255"));
  EXPECT_FALSE(is_loopback("128.0.0.1"));
  EXPECT_FALSE(is_loopback("0.0.0.0")) << "the wildcard is every interface";
  EXPECT_FALSE(is_loopback("10.0.0.127"));
  EXPECT_FALSE(is_loopback("192.168.1.10"));
}

TEST(Loopback, Ipv6) {
  EXPECT_TRUE(is_loopback("::1"));
  EXPECT_TRUE(is_loopback("0:0:0:0:0:0:0:1")) << "the same address, written out";
  EXPECT_TRUE(is_loopback("::ffff:127.0.0.1")) << "IPv4-mapped loopback";
  EXPECT_FALSE(is_loopback("::")) << "the IPv6 wildcard";
  EXPECT_FALSE(is_loopback("::ffff:10.0.0.1"));
  EXPECT_FALSE(is_loopback("fe80::1"));
  EXPECT_FALSE(is_loopback("::2"));
}

TEST(Loopback, OnlyExactNumericAddresses) {
  EXPECT_FALSE(is_loopback("localhost")) << "a name resolves to whatever the resolver says";
  EXPECT_FALSE(is_loopback("127.0.0.1.nip.io")) << "a name that starts like an address";
  EXPECT_FALSE(is_loopback("127.0.0.1 "));
  EXPECT_FALSE(is_loopback(" 127.0.0.1"));
  EXPECT_FALSE(is_loopback(std::string_view{"127.0.0.1\0garbage", 17}));
  EXPECT_FALSE(is_loopback("127.0.0.256"));
  EXPECT_FALSE(is_loopback(""));
}

TEST(BindCheck, LoopbackRules) {
  EXPECT_TRUE(check_bind("127.0.0.1", Security{.tokens = true}).empty());
  EXPECT_TRUE(check_bind("::1", Security{.allow_unauthenticated = true}).empty()) << "explicit, and local only";
  EXPECT_EQ(check_bind("127.0.0.1", Security{}).size(), 1U) << "no tokens and nothing explicit";
}

TEST(BindCheck, BeyondLoopbackNeedsTokensAndTls) {
  EXPECT_TRUE(check_bind("192.168.1.10", Security{.tokens = true, .tls = true}).empty());
  EXPECT_TRUE(check_bind("::", Security{.tokens = true, .tls = true}).empty());
  EXPECT_FALSE(check_bind("0.0.0.0", Security{.tokens = true}).empty()) << "tokens in clear";
  EXPECT_FALSE(check_bind("0.0.0.0", Security{.tls = true, .allow_unauthenticated = true}).empty())
      << "TLS without authentication: an encrypted channel to anyone";
  EXPECT_FALSE(check_bind("::", Security{.tokens = true, .tls = true, .allow_unauthenticated = true}).empty())
      << "--no-auth beyond loopback";
  EXPECT_FALSE(check_bind("::ffff:10.0.0.1", Security{.tokens = true}).empty());
  EXPECT_FALSE(check_bind("localhost", Security{.tokens = true, .tls = true}).empty()) << "not numeric";
  const auto p = check_bind("127.0.0.1.nip.io", Security{.tokens = true, .tls = true});
  ASSERT_EQ(p.size(), 1U);
  EXPECT_NE(p[0].find("not a numeric"), std::string::npos) << p[0];
}
