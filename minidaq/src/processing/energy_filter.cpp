// SPDX-License-Identifier: MIT
#include "minidaq/processing/energy_filter.hpp"

#include <bit>
#include <cstdint>
#include <cstring>

#if defined(__x86_64__)
#include <immintrin.h>
#define MINIDAQ_X86 1
#endif

namespace minidaq {
namespace {

// [snippet:branchy]
std::size_t filter_branchy(std::span<const Single> in, Single* out, float lo, float hi) noexcept {
  std::size_t k = 0;
  for (const Single& s : in) {
    const float e = s.energy.count();
    if (e >= lo && e <= hi) {  // unpredictable when about half the singles pass
      out[k++] = s;
    }
  }
  return k;
}
// [/snippet:branchy]

// [snippet:branchless]
std::size_t filter_branchless(std::span<const Single> in, Single* out, float lo, float hi) noexcept {
  std::size_t k = 0;
  for (const Single& s : in) {
    const float e = s.energy.count();
    out[k] = s;                                            // always write...
    k += static_cast<std::size_t>((e >= lo) & (e <= hi));  // ...but only keep it if it passes
  }
  return k;
}
// [/snippet:branchless]

#if MINIDAQ_X86
// Each Single is 16 bytes: time (8), crystal (4), energy (4). In a vector of
// floats, the energies are lanes 3, 7, 11 and 15.

// [snippet:avx2]
// Two singles per 256-bit register. The compare yields one bit per float
// lane; bits 3 and 7 are the two energies. If only the second single is kept,
// the two 128-bit halves are swapped so it moves to the front. The whole
// register is stored either way: the next store overwrites what was not kept.
__attribute__((target("avx2"))) std::size_t filter_avx2(std::span<const Single> in, Single* out, float lo,
                                                         float hi) noexcept {
  const __m256 vlo = _mm256_set1_ps(lo);
  const __m256 vhi = _mm256_set1_ps(hi);
  const std::size_t n = in.size();
  const Single* src = in.data();
  std::size_t i = 0;
  std::size_t k = 0;
  for (; i + 2 <= n; i += 2) {
    const __m256 v = _mm256_loadu_ps(reinterpret_cast<const float*>(src + i));
    const __m256 ok = _mm256_and_ps(_mm256_cmp_ps(v, vlo, _CMP_GE_OQ), _mm256_cmp_ps(v, vhi, _CMP_LE_OQ));
    const auto bits = static_cast<unsigned>(_mm256_movemask_ps(ok));
    const unsigned m = ((bits >> 3) & 1U) | ((bits >> 6) & 2U);
    const __m256 swapped = _mm256_permute2f128_ps(v, v, 0x01);
    const __m256 only_second = _mm256_castsi256_ps(_mm256_set1_epi32(-static_cast<int>(m == 2U)));
    _mm256_storeu_ps(reinterpret_cast<float*>(out + k), _mm256_blendv_ps(v, swapped, only_second));
    k += static_cast<std::size_t>(std::popcount(m));
  }
  return k + filter_branchless(in.subspan(i), out + k, lo, hi);
}
// [/snippet:avx2]

// [snippet:avx512]
// Four singles per 512-bit register. One mask bit per kept single becomes two
// bits per kept single in a 64-bit-lane mask (each single is two 64-bit lanes),
// and the compress instruction packs the kept lanes to the front.
__attribute__((target("avx512f"))) std::size_t filter_avx512(std::span<const Single> in, Single* out, float lo,
                                                             float hi) noexcept {
  const __m512 vlo = _mm512_set1_ps(lo);
  const __m512 vhi = _mm512_set1_ps(hi);
  const std::size_t n = in.size();
  const Single* src = in.data();
  std::size_t i = 0;
  std::size_t k = 0;
  for (; i + 4 <= n; i += 4) {
    const __m512 v = _mm512_loadu_ps(reinterpret_cast<const float*>(src + i));
    const __mmask16 ok = _mm512_mask_cmp_ps_mask(_mm512_cmp_ps_mask(v, vlo, _CMP_GE_OQ), v, vhi, _CMP_LE_OQ);
    const auto bits = static_cast<unsigned>(ok);
    // Energy lanes 3, 7, 11, 15 -> single bits 0..3 -> 64-bit lane pairs.
    const unsigned s = ((bits >> 3) & 1U) | ((bits >> 6) & 2U) | ((bits >> 9) & 4U) | ((bits >> 12) & 8U);
    unsigned q = 0;
    for (unsigned b = 0; b < 4; ++b) {
      q |= ((s >> b) & 1U) * (3U << (2 * b));
    }
    const __m512i packed = _mm512_maskz_compress_epi64(static_cast<__mmask8>(q), _mm512_castps_si512(v));
    _mm512_storeu_si512(out + k, packed);  // full store; see the note on in-place use
    k += static_cast<std::size_t>(std::popcount(s));
  }
  return k + filter_branchless(in.subspan(i), out + k, lo, hi);
}
// [/snippet:avx512]
#endif

}  // namespace

std::string_view to_string(FilterKernel k) noexcept {
  switch (k) {
    case FilterKernel::branchy: return "branchy";
    case FilterKernel::branchless: return "branchless";
    case FilterKernel::avx2: return "avx2";
    case FilterKernel::avx512: return "avx512";
    case FilterKernel::simd: return "simd";
    case FilterKernel::best: return "best";
  }
  return "?";
}

bool kernel_available(FilterKernel k) noexcept {
  switch (k) {
    case FilterKernel::branchy:
    case FilterKernel::branchless:
    case FilterKernel::simd:
    case FilterKernel::best:
      return true;
#if MINIDAQ_X86
    case FilterKernel::avx2:
      return __builtin_cpu_supports("avx2") != 0;
    case FilterKernel::avx512:
      return __builtin_cpu_supports("avx512f") != 0;
#else
    default:
      return false;
#endif
  }
  return false;
}

FilterKernel simd_kernel() noexcept {
  // [snippet:dispatch]
  // Decided once: the CPU does not change while we run.
  static const FilterKernel widest = [] {
    if (kernel_available(FilterKernel::avx512)) {
      return FilterKernel::avx512;
    }
    if (kernel_available(FilterKernel::avx2)) {
      return FilterKernel::avx2;
    }
    return FilterKernel::branchless;
  }();
  // [/snippet:dispatch]
  return widest;
}

FilterKernel best_kernel() noexcept {
  // Measured in Chapter 5: on 16-byte singles (AoS), the AVX2 and AVX-512
  // kernels are no faster than the branchless loop, in cache or from memory.
  // Revisit when the layout changes.
  return FilterKernel::branchless;
}

std::size_t filter_energy(std::span<const Single> in, std::span<Single> out, EnergyWindow w,
                          FilterKernel k) noexcept {
  if (out.size() < in.size()) {
    in = in.first(out.size());  // contract violation: never write past `out`
  }
  if (k == FilterKernel::best) {
    k = best_kernel();
  } else if (k == FilterKernel::simd || !kernel_available(k)) {
    k = simd_kernel();
  }
  const float lo = w.lo.count();
  const float hi = w.hi.count();
  switch (k) {
    case FilterKernel::branchy: return filter_branchy(in, out.data(), lo, hi);
#if MINIDAQ_X86
    case FilterKernel::avx2: return filter_avx2(in, out.data(), lo, hi);
    case FilterKernel::avx512: return filter_avx512(in, out.data(), lo, hi);
#endif
    default: return filter_branchless(in, out.data(), lo, hi);
  }
}

}  // namespace minidaq
