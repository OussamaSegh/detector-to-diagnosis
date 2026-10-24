// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <limits>
#include <random>
#include <vector>

#include "filters.hpp"

namespace {

using Kernel = std::size_t (*)(std::span<const ex::Single>, std::span<ex::Single>, float, float) noexcept;
struct Named {
  const char* name;
  Kernel fn;
};
const Named kernels[] = {{"branchy", ex::filter_branchy}, {"branchless", ex::filter_branchless},
                         {"simd", ex::filter_simd}};

std::vector<ex::Single> random_singles(std::size_t n, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::uniform_real_distribution<float> e{0.0F, 1000.0F};
  std::vector<ex::Single> v(n);
  for (std::size_t i = 0; i < n; ++i) {
    v[i] = ex::Single{minidaq::Picoseconds{static_cast<std::int64_t>(i)}, minidaq::CrystalId{static_cast<std::uint32_t>(i)},
                      minidaq::KeV{e(rng)}};
  }
  return v;
}

std::vector<ex::Single> reference(const std::vector<ex::Single>& in, float lo, float hi) {
  std::vector<ex::Single> out;
  for (const auto& s : in) {
    if (s.energy.count() >= lo && s.energy.count() <= hi) {
      out.push_back(s);
    }
  }
  return out;
}

std::vector<ex::Single> run(const Named& k, const std::vector<ex::Single>& in, float lo, float hi) {
  std::vector<ex::Single> out(in.size());
  out.resize(k.fn(in, out, lo, hi));
  return out;
}

}  // namespace

TEST(Filters, EverySizeFromZeroToForty) {
  for (std::size_t n = 0; n <= 40; ++n) {
    const auto in = random_singles(n, n + 11);
    const auto expected = reference(in, 400.0F, 650.0F);
    for (const auto& k : kernels) {
      EXPECT_EQ(run(k, in, 400.0F, 650.0F), expected) << k.name << " n=" << n;
    }
  }
}

TEST(Filters, BoundariesNanAndInfinity) {
  const float nan = std::numeric_limits<float>::quiet_NaN();
  const float inf = std::numeric_limits<float>::infinity();
  std::vector<ex::Single> in;
  for (const float e : {400.0F, 399.9F, 650.0F, 650.1F, nan, inf, -inf, 511.0F, nan}) {
    in.push_back(ex::Single{minidaq::Picoseconds{0}, minidaq::CrystalId{0}, minidaq::KeV{e}});
  }
  for (const auto& k : kernels) {
    const auto out = run(k, in, 400.0F, 650.0F);
    ASSERT_EQ(out.size(), 3U) << k.name;
    EXPECT_EQ(out[0].energy.count(), 400.0F) << k.name;
    EXPECT_EQ(out[1].energy.count(), 650.0F) << k.name;
    EXPECT_EQ(out[2].energy.count(), 511.0F) << k.name;
  }
}

TEST(Filters, HundredThousandRandomSingles) {
  const auto in = random_singles(100'000, 99);
  for (const float a : {10.0F, 50.0F, 90.0F}) {
    const float lo = 500.0F - 5.0F * a;
    const float hi = 500.0F + 5.0F * a;
    const auto expected = reference(in, lo, hi);
    for (const auto& k : kernels) {
      EXPECT_EQ(run(k, in, lo, hi), expected) << k.name << " accept " << a;
    }
  }
}
