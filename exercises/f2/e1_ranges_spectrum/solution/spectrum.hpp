// Exercise F2.1, solution: an energy spectrum with ranges, views and std::ranges::to.
#pragma once

#include <cstdint>
#include <ranges>
#include <span>
#include <vector>
#include <version>

namespace ex {

struct Single {
  std::int64_t time_ps = 0;
  std::uint32_t crystal = 0;
  float energy_kev = 0.0F;
};

struct Binning {
  float lo;  // inclusive
  float hi;  // exclusive
  std::size_t bins;
};

// [snippet:to]
// std::ranges::to is C++23 (GCC 14, libc++ 17). With an older library, the same call is
// spelled with the vector's iterator-pair constructor; the feature-test macro picks one.
template <typename R>
auto to_vector(R&& r) {
#if defined(__cpp_lib_ranges_to_container)
  return std::ranges::to<std::vector>(std::forward<R>(r));
#else
  auto common = std::forward<R>(r) | std::views::common;
  return std::vector<std::ranges::range_value_t<R> >(common.begin(), common.end());
#endif
}
// [/snippet:to]

// [snippet:spectrum]
inline auto in_window(float lo, float hi) {
  return std::views::filter(
      [lo, hi](const Single& s) { return s.energy_kev >= lo && s.energy_kev <= hi; });
}

inline std::vector<float> energies_in_window(std::span<const Single> s, float lo, float hi) {
  return to_vector(s | in_window(lo, hi) | std::views::transform(&Single::energy_kev));
}

inline std::vector<std::size_t> spectrum(std::span<const Single> s, Binning b) {
  std::vector<std::size_t> h(b.bins, 0);
  const float width = (b.hi - b.lo) / static_cast<float>(b.bins);
  auto in_range = [b](float e) { return e >= b.lo && e < b.hi; };
  auto bin_of = [b, width](float e) {
    const auto i = static_cast<std::size_t>((e - b.lo) / width);
    return i < b.bins ? i : b.bins - 1;  // rounding at the top edge stays in the last bin
  };
  for (std::size_t i : s | std::views::transform(&Single::energy_kev) |
                           std::views::filter(in_range) | std::views::transform(bin_of)) {
    ++h[i];
  }
  return h;
}
// [/snippet:spectrum]

inline double photopeak_fraction(std::span<const Single> s, float lo, float hi) {
  if (s.empty()) return 0.0;
  const auto n = std::ranges::distance(s | in_window(lo, hi));
  return static_cast<double>(n) / static_cast<double>(s.size());
}

}  // namespace ex
