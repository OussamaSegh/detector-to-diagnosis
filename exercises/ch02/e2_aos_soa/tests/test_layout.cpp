#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "layout.hpp"

namespace {
std::vector<ex::Single> sample(std::size_t n) {
  std::vector<ex::Single> v(n);
  for (std::size_t i = 0; i < n; ++i) {
    v[i] = ex::Single{static_cast<std::int64_t>(i) * 31, static_cast<std::uint32_t>(i % 18432),
                      400.0F + static_cast<float>(i % 300)};
  }
  return v;
}
}  // namespace

TEST(Layout, ToSoaPreservesFields) {
  const auto aos = sample(1000);
  const ex::SinglesSoA soa = ex::to_soa(aos);
  ASSERT_EQ(soa.energy_kev.size(), aos.size());
  ASSERT_EQ(soa.time_ps.size(), aos.size());
  ASSERT_EQ(soa.crystal.size(), aos.size());
  for (std::size_t i = 0; i < aos.size(); ++i) {
    EXPECT_EQ(soa.time_ps[i], aos[i].time_ps);
    EXPECT_EQ(soa.crystal[i], aos[i].crystal);
    EXPECT_EQ(soa.energy_kev[i], aos[i].energy_kev);
  }
}

TEST(Layout, SumsAgree) {
  const auto aos = sample(100'000);
  double ref = 0.0;
  for (const auto& s : aos) {
    ref += static_cast<double>(s.energy_kev);
  }
  EXPECT_NEAR(ex::sum_energy(aos), ref, 1e-9 * ref);
  EXPECT_NEAR(ex::sum_energy(ex::to_soa(aos)), ref, 1e-9 * ref);
}
