// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <random>
#include <vector>

#include "minidaq/processing/energy_filter.hpp"

using minidaq::CrystalId;
using minidaq::EnergyWindow;
using minidaq::FilterKernel;
using minidaq::KeV;
using minidaq::Picoseconds;
using minidaq::Single;

namespace {

constexpr FilterKernel all_kernels[] = {FilterKernel::branchy, FilterKernel::branchless, FilterKernel::avx2,
                                        FilterKernel::avx512, FilterKernel::simd, FilterKernel::best};

std::vector<Single> random_singles(std::size_t n, std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::uniform_real_distribution<float> e{0.0F, 1000.0F};
  std::vector<Single> v(n);
  for (std::size_t i = 0; i < n; ++i) {
    v[i] = Single{Picoseconds{static_cast<std::int64_t>(i) * 100}, CrystalId{static_cast<std::uint32_t>(i % 5000)},
                  KeV{e(rng)}};
  }
  return v;
}

std::vector<Single> reference(const std::vector<Single>& in, EnergyWindow w) {
  std::vector<Single> out;
  for (const Single& s : in) {
    if (s.energy.count() >= w.lo.count() && s.energy.count() <= w.hi.count()) {
      out.push_back(s);
    }
  }
  return out;
}

}  // namespace

TEST(EnergyFilter, AllKernelsMatchTheReferenceForEverySize) {
  // REQ: SRS-PROC-001
  const EnergyWindow w{};
  for (std::size_t n = 0; n <= 37; ++n) {
    const auto in = random_singles(n, n + 1);
    const auto expected = reference(in, w);
    for (const auto k : all_kernels) {
      std::vector<Single> out(n);
      const std::size_t kept = minidaq::filter_energy(in, out, w, k);
      out.resize(kept);
      EXPECT_EQ(out, expected) << to_string(k) << " n=" << n;
    }
  }
}

TEST(EnergyFilter, BoundariesAreInclusiveAndNanIsRejected) {
  const EnergyWindow w{KeV{400.0F}, KeV{650.0F}};
  const float nan = std::numeric_limits<float>::quiet_NaN();
  const float inf = std::numeric_limits<float>::infinity();
  std::vector<Single> in;
  for (const float e : {399.99F, 400.0F, 511.0F, 650.0F, 650.01F, nan, inf, -inf, 0.0F, 500.0F}) {
    in.push_back(Single{Picoseconds{0}, CrystalId{1}, KeV{e}});
  }
  for (const auto k : all_kernels) {
    std::vector<Single> out(in.size());
    out.resize(minidaq::filter_energy(in, out, w, k));
    ASSERT_EQ(out.size(), 4U) << to_string(k);
    EXPECT_EQ(out[0].energy.count(), 400.0F);
    EXPECT_EQ(out[1].energy.count(), 511.0F);
    EXPECT_EQ(out[2].energy.count(), 650.0F);
    EXPECT_EQ(out[3].energy.count(), 500.0F);
  }
}

TEST(EnergyFilter, InPlaceMatchesOutOfPlace) {
  const EnergyWindow w{};
  const auto in = random_singles(10'001, 7);
  const auto expected = reference(in, w);
  for (const auto k : all_kernels) {
    auto buf = in;
    buf.resize(minidaq::filter_energy(buf, buf, w, k));
    EXPECT_EQ(buf, expected) << to_string(k);
  }
}

TEST(EnergyFilter, NeverWritesPastAShortOutput) {
  const auto in = random_singles(64, 3);
  std::vector<Single> out(16 + 4);
  const Single guard{Picoseconds{-1}, CrystalId{9}, KeV{-1.0F}};
  for (const auto k : all_kernels) {
    std::fill(out.begin(), out.end(), guard);
    const std::size_t kept = minidaq::filter_energy(in, std::span(out).first(16), EnergyWindow{KeV{0.0F}, KeV{2000.0F}}, k);
    EXPECT_EQ(kept, 16U) << to_string(k);
    for (std::size_t i = 16; i < out.size(); ++i) {
      EXPECT_EQ(out[i], guard) << to_string(k) << " wrote past the output at " << i;
    }
  }
}

TEST(EnergyFilter, SimdAndBestAreAvailableAndResolved) {
  EXPECT_TRUE(minidaq::kernel_available(FilterKernel::simd));
  EXPECT_TRUE(minidaq::kernel_available(FilterKernel::best));
  const FilterKernel simd = minidaq::simd_kernel();
  EXPECT_TRUE(simd == FilterKernel::avx512 || simd == FilterKernel::avx2 || simd == FilterKernel::branchless);
  EXPECT_TRUE(minidaq::kernel_available(simd));
  EXPECT_EQ(minidaq::best_kernel(), FilterKernel::branchless) << "the measured default (Chapter 5)";
  RecordProperty("simd_kernel", std::string{to_string(simd)});
}
