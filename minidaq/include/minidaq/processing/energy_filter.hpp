// SPDX-License-Identifier: MIT
// MiniDAQ - energy window filter for singles (Chapter 5).
//
// Keeps the singles whose energy lies in [lo, hi] (inclusive), in order. Four
// kernels compute the same result: a plain loop with a branch, a branchless
// loop, and AVX2 and AVX-512 versions selected at run time when the CPU has
// them. Chapter 5 measures why each one exists, and why the default is the
// branchless loop: on 16-byte singles the SIMD kernels are not faster.
#pragma once

#include <cstddef>
#include <span>
#include <string_view>

#include "minidaq/core/single.hpp"

namespace minidaq {

struct EnergyWindow {
  // Typical LYSO window around 511 keV (assumption: confirm with team).
  KeV lo{400.0F};
  KeV hi{650.0F};
};

// `simd`: the widest SIMD kernel this CPU has (branchless if none).
// `best`: the measured default, the branchless kernel (Chapter 5).
enum class FilterKernel : unsigned char { branchy, branchless, avx2, avx512, simd, best };

[[nodiscard]] std::string_view to_string(FilterKernel k) noexcept;
// True if this CPU (and this build) can run kernel k. `simd` and `best` are
// always available.
[[nodiscard]] bool kernel_available(FilterKernel k) noexcept;
// The kernel `simd` resolves to on this CPU.
[[nodiscard]] FilterKernel simd_kernel() noexcept;
// The kernel `best` resolves to.
[[nodiscard]] FilterKernel best_kernel() noexcept;

// Copies the singles of `in` whose energy is in the window to the front of
// `out` and returns how many. Requires out.size() >= in.size(); `out` may be
// the same memory as `in` (in-place filtering). NaN energies are rejected.
// An unavailable kernel falls back to `simd`'s choice.
std::size_t filter_energy(std::span<const Single> in, std::span<Single> out, EnergyWindow w,
                          FilterKernel k = FilterKernel::best) noexcept;

}  // namespace minidaq
