// SPDX-License-Identifier: MIT
// Exercise 5.1 solution. The library's minidaq::filter_energy holds the same
// kernels plus an AVX-512 one; this version keeps AVX2 for portability.
#include "filters.hpp"

#include <bit>

#if defined(__x86_64__)
#include <immintrin.h>
#endif

namespace ex {

std::size_t filter_branchy(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
  std::size_t k = 0;
  for (const Single& s : in) {
    const float e = s.energy.count();
    if (e >= lo && e <= hi) {
      out[k++] = s;
    }
  }
  return k;
}

// [snippet:branchless]
std::size_t filter_branchless(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
  std::size_t k = 0;
  Single* dst = out.data();
  for (const Single& s : in) {
    const float e = s.energy.count();
    dst[k] = s;
    k += static_cast<std::size_t>((e >= lo) & (e <= hi));
  }
  return k;
}
// [/snippet:branchless]

#if defined(__x86_64__)
namespace {
__attribute__((target("avx2"))) std::size_t filter_avx2(std::span<const Single> in, Single* out, float lo,
                                                         float hi) noexcept {
  const __m256 vlo = _mm256_set1_ps(lo);
  const __m256 vhi = _mm256_set1_ps(hi);
  std::size_t i = 0;
  std::size_t k = 0;
  for (; i + 2 <= in.size(); i += 2) {
    const __m256 v = _mm256_loadu_ps(reinterpret_cast<const float*>(in.data() + i));
    const __m256 ok = _mm256_and_ps(_mm256_cmp_ps(v, vlo, _CMP_GE_OQ), _mm256_cmp_ps(v, vhi, _CMP_LE_OQ));
    const auto bits = static_cast<unsigned>(_mm256_movemask_ps(ok));
    const unsigned m = ((bits >> 3) & 1U) | ((bits >> 6) & 2U);  // energies are float lanes 3 and 7
    const __m256 swapped = _mm256_permute2f128_ps(v, v, 0x01);
    const __m256 only_second = _mm256_castsi256_ps(_mm256_set1_epi32(-static_cast<int>(m == 2U)));
    _mm256_storeu_ps(reinterpret_cast<float*>(out + k), _mm256_blendv_ps(v, swapped, only_second));
    k += static_cast<std::size_t>(std::popcount(m));
  }
  for (; i < in.size(); ++i) {
    const float e = in[i].energy.count();
    out[k] = in[i];
    k += static_cast<std::size_t>((e >= lo) & (e <= hi));
  }
  return k;
}
}  // namespace
#endif

// [snippet:simd]
std::size_t filter_simd(std::span<const Single> in, std::span<Single> out, float lo, float hi) noexcept {
#if defined(__x86_64__)
  if (__builtin_cpu_supports("avx2")) {
    return filter_avx2(in, out.data(), lo, hi);
  }
#endif
  return filter_branchless(in, out, lo, hi);
}
// [/snippet:simd]

}  // namespace ex
