// Exercise F1.3, starter: answer each question with a standard algorithm (<algorithm>,
// <numeric>, std::erase_if) instead of a hand-written loop. Every function below is a stub.
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

// How many singles have lo <= energy <= hi? (std::ranges::count_if)
inline std::size_t count_in_window(std::span<const Single> s, float lo, float hi) {
  return 0;  // TODO
}

// The single with the highest energy, or nothing for an empty batch. (std::ranges::max_element)
inline std::optional<Single> highest_energy(std::span<const Single> s) {
  return std::nullopt;  // TODO
}

// The mean energy, or nothing for an empty batch. (std::accumulate)
inline std::optional<double> mean_energy(std::span<const Single> s) {
  return std::nullopt;  // TODO
}

// Sort by time, and by crystal among equal times. (std::ranges::sort with a comparison)
inline void sort_by_time(std::vector<Single>& s) {
  // TODO
}

// Is the batch in that order? (std::ranges::is_sorted)
inline bool is_time_ordered(std::span<const Single> s) {
  return true;  // TODO
}

// Remove the singles outside [lo, hi], keeping the order of the rest. (std::erase_if)
inline void drop_outside_window(std::vector<Single>& s, float lo, float hi) {
  // TODO
}

// How many singles per crystal? (a std::unordered_map)
inline std::unordered_map<std::uint32_t, std::size_t> counts_per_crystal(
    std::span<const Single> s) {
  return {};  // TODO
}

}  // namespace ex
