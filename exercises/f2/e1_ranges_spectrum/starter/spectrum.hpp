// Exercise F2.1, starter: write the spectrum with views (std::views::filter, transform) and
// collect a view into a vector with std::ranges::to where the library has it.
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

// TODO: collect any range into a std::vector: std::ranges::to<std::vector> when
// __cpp_lib_ranges_to_container is defined, the iterator-pair constructor otherwise.
template <typename R>
auto to_vector(R&& r) {
  return std::vector<std::ranges::range_value_t<R>>{};
}

// The energies of the singles with lo <= energy <= hi, in their order.
inline std::vector<float> energies_in_window(std::span<const Single> s, float lo, float hi) {
  return {};  // TODO: filter, transform, to_vector
}

// A histogram of the energies in [lo, hi) with b.bins equal bins.
inline std::vector<std::size_t> spectrum(std::span<const Single> s, Binning b) {
  return std::vector<std::size_t>(b.bins, 0);  // TODO
}

// The fraction of singles in [lo, hi] (inclusive); 0 for an empty batch.
inline double photopeak_fraction(std::span<const Single> s, float lo, float hi) {
  return 0.0;  // TODO
}

}  // namespace ex
