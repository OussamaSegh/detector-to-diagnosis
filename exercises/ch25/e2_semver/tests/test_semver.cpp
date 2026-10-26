// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 25.2: Semantic Versioning 2.0.0 precedence, including the example
// chain of its section 11, and the versions it does not allow.
#include <gtest/gtest.h>

#include <vector>

#include "semver.hpp"

using namespace semver;

namespace {

Version v(const char* text) {
  const auto parsed = parse(text);
  EXPECT_TRUE(parsed.has_value()) << text;
  return parsed.value_or(Version{});
}

}  // namespace

TEST(SemVer, ParsesTheParts) {
  const auto x = v("1.20.300-rc.1.x-y+build.5");
  EXPECT_EQ(x.major, 1U);
  EXPECT_EQ(x.minor, 20U);
  EXPECT_EQ(x.patch, 300U);
  EXPECT_EQ(x.pre, (std::vector<std::string>{"rc", "1", "x-y"}));
  EXPECT_EQ(x.build, "build.5");
  EXPECT_TRUE(v("0.0.0").pre.empty());
  EXPECT_EQ(v("1.0.0+0017").build, "0017") << "leading zeros are fine in build metadata";
}

TEST(SemVer, RefusesWhatTheSpecificationDoesNotAllow) {
  for (const char* bad : {"", "1", "1.2", "1.2.3.4", "01.2.3", "1.02.3", "1.2.03", "1.2.3-",
                          "1.2.3-rc..1", "1.2.3-01", "1.2.3+", "1.2.3+a..b", "1.2.3-r@c", "v1.2.3",
                          "1.2.-3", "18446744073709551616.0.0", " 1.2.3"}) {
    EXPECT_FALSE(parse(bad).has_value()) << '"' << bad << '"';
  }
  EXPECT_TRUE(parse("18446744073709551615.0.0").has_value()) << "the largest 64-bit number";
}

TEST(SemVer, TheChainOfSection11) {
  const std::vector<const char*> chain{"1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
                                       "1.0.0-beta",  "1.0.0-beta.2",  "1.0.0-beta.11",
                                       "1.0.0-rc.1",  "1.0.0"};
  for (std::size_t i = 0; i + 1 < chain.size(); ++i) {
    EXPECT_EQ(compare(v(chain[i]), v(chain[i + 1])), std::strong_ordering::less)
        << chain[i] << " < " << chain[i + 1];
    EXPECT_EQ(compare(v(chain[i + 1]), v(chain[i])), std::strong_ordering::greater);
  }
}

TEST(SemVer, NumbersCompareAsNumbers) {
  EXPECT_EQ(compare(v("1.9.0"), v("1.10.0")), std::strong_ordering::less);
  EXPECT_EQ(compare(v("0.5.0-rc.2"), v("0.5.0-rc.10")), std::strong_ordering::less)
      << "the case string comparison gets wrong";
  EXPECT_EQ(compare(v("1.0.0-2"), v("1.0.0-10")), std::strong_ordering::less);
  EXPECT_EQ(compare(v("1.0.0-9999"), v("1.0.0-a")), std::strong_ordering::less)
      << "numeric identifiers are lower than alphanumeric ones";
  EXPECT_EQ(compare(v("1.0.0-rc.1"), v("1.0.0-rc.1.0")), std::strong_ordering::less)
      << "fewer identifiers, lower";
}

TEST(SemVer, BuildMetadataHasNoPrecedence) {
  EXPECT_EQ(compare(v("1.0.0+a"), v("1.0.0+b")), std::strong_ordering::equal);
  EXPECT_EQ(compare(v("1.0.0-rc.1+z"), v("1.0.0-rc.1")), std::strong_ordering::equal);
  EXPECT_EQ(compare(v("1.0.0+zzz"), v("1.0.1")), std::strong_ordering::less);
}
