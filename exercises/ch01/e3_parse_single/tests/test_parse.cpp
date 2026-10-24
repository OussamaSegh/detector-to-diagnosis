#include <gtest/gtest.h>

#include <array>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <random>
#include <vector>

#include "parse.hpp"

using ex::parse_single;
using ex::ParseError;
using ex::Single;

namespace {
std::array<std::byte, 16> encode(std::int64_t t, std::uint32_t c, float e) {
  std::array<std::byte, 16> b{};
  std::memcpy(b.data(), &t, 8);  // the test machine is little-endian (checked below)
  std::memcpy(b.data() + 8, &c, 4);
  std::memcpy(b.data() + 12, &e, 4);
  return b;
}
static_assert(std::endian::native == std::endian::little);
std::vector<std::byte> vec(const std::array<std::byte, 16>& a) { return {a.begin(), a.end()}; }
}  // namespace

TEST(ParseSingle, RoundTrip) {
  const auto b = encode(42'000, 17'000, 511.0F);
  const auto r = parse_single(b);
  ASSERT_TRUE(r);
  EXPECT_EQ(r->time_ps, 42'000);
  EXPECT_EQ(r->crystal, 17'000U);
  EXPECT_FLOAT_EQ(r->energy_kev, 511.0F);
}

TEST(ParseSingle, TenMalformedInputs) {
  const auto nan = std::numeric_limits<float>::quiet_NaN();
  const auto inf = std::numeric_limits<float>::infinity();
  const auto good = encode(1, 1, 511.0F);
  struct Case {
    std::vector<std::byte> bytes;
    ParseError expected;
  };
  const std::vector<Case> cases = {
      {{}, ParseError::truncated},
      {{good.begin(), good.begin() + 8}, ParseError::truncated},
      {{good.begin(), good.begin() + 15}, ParseError::truncated},
      {vec(encode(-1, 1, 511.0F)), ParseError::negative_time},
      {vec(encode(std::numeric_limits<std::int64_t>::min(), 1, 1.0F)),
       ParseError::negative_time},
      {vec(encode(1, 18432, 511.0F)), ParseError::crystal_out_of_range},
      {vec(encode(1, 0xFFFFFFFFU, 511.0F)),
       ParseError::crystal_out_of_range},
      {vec(encode(1, 1, nan)), ParseError::energy_not_finite},
      {vec(encode(1, 1, -inf)), ParseError::energy_not_finite},
      {vec(encode(1, 1, 2000.01F)), ParseError::energy_out_of_range},
  };
  ASSERT_EQ(cases.size(), 10U);
  for (std::size_t i = 0; i < cases.size(); ++i) {
    const auto r = parse_single(cases[i].bytes);
    ASSERT_FALSE(r) << "case " << i << " was accepted";
    EXPECT_EQ(r.error(), cases[i].expected) << "case " << i;
  }
}

TEST(ParseSingle, MutationFuzzNeverCrashesAndKeepsInvariants) {
  std::mt19937_64 rng{20261026};  // fixed seed: failures are reproducible
  std::uniform_int_distribution<int> byte_dist(0, 255);
  std::uniform_int_distribution<std::size_t> pos_dist(0, 15);
  std::uniform_int_distribution<std::size_t> len_dist(0, 16);
  std::size_t accepted = 0;
  for (int i = 0; i < 200'000; ++i) {
    auto b = encode(static_cast<std::int64_t>(rng() >> 2), static_cast<std::uint32_t>(rng() % 18432),
                    511.0F);
    const int flips = 1 + (i % 4);
    for (int f = 0; f < flips; ++f) {
      b[pos_dist(rng)] = static_cast<std::byte>(byte_dist(rng));
    }
    // Copy into an exactly-sized heap buffer so ASan catches any over-read.
    const std::size_t len = (i % 10 == 0) ? len_dist(rng) : 16;
    std::vector<std::byte> heap(b.begin(), b.begin() + static_cast<std::ptrdiff_t>(len));
    const auto r = parse_single(heap);
    if (r) {
      ++accepted;
      ASSERT_EQ(len, 16U);
      ASSERT_GE(r->time_ps, 0);
      ASSERT_LT(r->crystal, 18432U);
      ASSERT_TRUE(std::isfinite(r->energy_kev));
      ASSERT_GE(r->energy_kev, 0.0F);
      ASSERT_LE(r->energy_kev, 2000.0F);
    }
  }
  EXPECT_GT(accepted, 1000U);  // the fuzz loop must also exercise the success path
}
