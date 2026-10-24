// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <string>
#include <vector>

#include "event_source.hpp"

#if defined(__SANITIZE_ADDRESS__) || defined(__SANITIZE_THREAD__)
#define EX_SANITIZED 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer) || __has_feature(thread_sanitizer)
#define EX_SANITIZED 1
#endif
#endif

namespace {

constexpr std::size_t kN = 1'000'000;

std::vector<ex::Single> generate(const ex::SourceConfig& cfg, std::size_t n = kN) {
  ex::EventSource src{cfg};
  std::vector<ex::Single> v(n);
  // In pieces of odd sizes, so that a pending partner crosses calls.
  std::size_t done = 0;
  std::size_t piece = 1;
  while (done < n) {
    const std::size_t m = std::min(piece, n - done);
    src.generate(std::span(v).subspan(done, m));
    done += m;
    piece = piece * 3 % 4099 + 1;
  }
  return v;
}

bool is_partner(const ex::Single& a, const ex::Single& b, const ex::SourceConfig& cfg) {
  const std::uint32_t r = cfg.crystals_per_ring;
  const auto ca = a.crystal.value();
  const auto cb = b.crystal.value();
  const auto dt = b.time.count() - a.time.count();
  return ca / r == cb / r && (ca % r + r / 2) % r == cb % r && dt >= 0 && dt < cfg.pair_spread_ps;
}

}  // namespace

TEST(EventSource, TimeOrderedAndDeterministic) {
  const ex::SourceConfig cfg{};
  const auto a = generate(cfg);
  EXPECT_TRUE(std::is_sorted(a.begin(), a.end(), [](const ex::Single& x, const ex::Single& y) { return x.time < y.time; }));
  EXPECT_EQ(a, generate(cfg));
  ex::SourceConfig other = cfg;
  other.seed = 2;
  EXPECT_NE(a, generate(other));
}

TEST(EventSource, RateAndPairFraction) {
  const ex::SourceConfig cfg{};
  const auto v = generate(cfg);
  std::size_t primaries = 0;
  std::size_t pairs = 0;
  for (std::size_t i = 0; i < v.size(); ++i) {
    ++primaries;
    if (i + 1 < v.size() && is_partner(v[i], v[i + 1], cfg)) {
      ++pairs;
      ++i;  // skip the partner
    }
  }
  const double pair_fraction = static_cast<double>(pairs) / static_cast<double>(primaries);
  EXPECT_NEAR(pair_fraction, cfg.pair_fraction, 0.005);
  // Primaries arrive at rate_hz: elapsed time over primaries is the mean gap (100,000 ps).
  const double mean_gap = static_cast<double>(v.back().time.count() - v.front().time.count()) /
                          static_cast<double>(primaries);
  EXPECT_NEAR(mean_gap, 1e12 / cfg.rate_hz, 1e12 / cfg.rate_hz * 0.01);
}

TEST(EventSource, EnergyIsNormal511Sigma25) {
  const auto v = generate({});
  double sum = 0.0;
  double sum2 = 0.0;
  std::size_t in1 = 0;
  std::size_t in2 = 0;
  for (const auto& s : v) {
    const auto e = static_cast<double>(s.energy.count());
    sum += e;
    sum2 += e * e;
    in1 += std::fabs(e - 511.0) <= 25.0 ? 1U : 0U;
    in2 += std::fabs(e - 511.0) <= 50.0 ? 1U : 0U;
  }
  const double n = static_cast<double>(v.size());
  const double mean = sum / n;
  EXPECT_NEAR(mean, 511.0, 0.2);
  EXPECT_NEAR(std::sqrt(sum2 / n - mean * mean), 25.0, 0.2);
  EXPECT_NEAR(static_cast<double>(in1) / n, 0.6827, 0.003);
  EXPECT_NEAR(static_cast<double>(in2) / n, 0.9545, 0.002);
}

TEST(EventSource, CrystalsAreUniform) {
  const ex::SourceConfig cfg{};
  const auto v = generate(cfg);
  std::vector<std::size_t> bins(16);
  for (const auto& s : v) {
    ASSERT_LT(s.crystal.value(), cfg.crystals);
    ++bins[s.crystal.value() * 16 / cfg.crystals];
  }
  for (const auto b : bins) {
    EXPECT_NEAR(static_cast<double>(b), static_cast<double>(v.size()) / 16.0, static_cast<double>(v.size()) / 16.0 * 0.02);
  }
}

// The performance acceptance test: at most 18 ns per single (a third of the
// starter's 53.5 ns on the book's machine), best of 5 runs. On another machine,
// time the starter first and set EX_NS_PER_SINGLE to a third of its result.
// Only meaningful in an optimized, uninstrumented build.
TEST(EventSource, FastEnough) {
#if !defined(NDEBUG) || defined(EX_SANITIZED)
  GTEST_SKIP() << "speed is only checked in release builds without sanitizers";
#else
  ex::EventSource src{{}};
  std::vector<ex::Single> v(kN);
  double best = 1e9;
  for (int rep = 0; rep < 5; ++rep) {
    const auto t0 = std::chrono::steady_clock::now();
    src.generate(v);
    const auto t1 = std::chrono::steady_clock::now();
    best = std::min(best, std::chrono::duration<double, std::nano>(t1 - t0).count() / static_cast<double>(kN));
  }
  const char* env = std::getenv("EX_NS_PER_SINGLE");
  const double budget = env != nullptr ? std::atof(env) : 18.0;
  RecordProperty("ns_per_single", std::to_string(best));
  EXPECT_LT(best, budget) << "ns per single (best of 5)";
#endif
}
