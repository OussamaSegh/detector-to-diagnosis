// Exercise F1.3, solution: the questions a DAQ asks of a batch of singles, each answered by one
// standard algorithm instead of a hand-written loop.
#pragma once

#include <algorithm>
#include <cstdint>
#include <numeric>
#include <optional>
#include <span>
#include <unordered_map>
#include <vector>

namespace ex {

struct Single {
  std::int64_t time_ps = 0;
  std::uint32_t crystal = 0;
  float energy_kev = 0.0F;
};

// [snippet:algorithms]
inline std::size_t count_in_window(std::span<const Single> s, float lo, float hi) {
  return static_cast<std::size_t>(std::ranges::count_if(
      s, [lo, hi](const Single& x) { return x.energy_kev >= lo && x.energy_kev <= hi; }));
}

inline std::optional<Single> highest_energy(std::span<const Single> s) {
  if (s.empty()) return std::nullopt;
  return *std::ranges::max_element(s, {}, &Single::energy_kev);
}

inline std::optional<double> mean_energy(std::span<const Single> s) {
  if (s.empty()) return std::nullopt;
  const double sum = std::accumulate(s.begin(), s.end(), 0.0, [](double acc, const Single& x) {
    return acc + static_cast<double>(x.energy_kev);
  });
  return sum / static_cast<double>(s.size());
}

inline bool time_then_crystal(const Single& a, const Single& b) {
  return a.time_ps != b.time_ps ? a.time_ps < b.time_ps : a.crystal < b.crystal;
}

inline void sort_by_time(std::vector<Single>& s) { std::ranges::sort(s, time_then_crystal); }

inline bool is_time_ordered(std::span<const Single> s) {
  return std::ranges::is_sorted(s, time_then_crystal);
}

inline void drop_outside_window(std::vector<Single>& s, float lo, float hi) {
  std::erase_if(s, [lo, hi](const Single& x) { return x.energy_kev < lo || x.energy_kev > hi; });
}
// [/snippet:algorithms]

inline std::unordered_map<std::uint32_t, std::size_t> counts_per_crystal(
    std::span<const Single> s) {
  std::unordered_map<std::uint32_t, std::size_t> counts;
  for (const auto& x : s) ++counts[x.crystal];  // a loop is the clearest form of a histogram
  return counts;
}

}  // namespace ex
