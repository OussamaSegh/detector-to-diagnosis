#pragma once
// Exercise 2.1 solution. See ANSWER.md for the interpretation.
#include <cstddef>

namespace ex {

struct Budget {
  double bytes_per_s;
  double gib_per_s;   // 1 GiB = 2^30 bytes
  double gbit_per_s;  // 1 Gbit = 10^9 bits (network convention)
  std::size_t records_per_cache_line;
};

inline constexpr std::size_t kCacheLine = 64;

constexpr Budget stream_budget(double records_per_s, std::size_t bytes_per_record) {
  const double bytes = records_per_s * static_cast<double>(bytes_per_record);
  return Budget{bytes, bytes / (1024.0 * 1024.0 * 1024.0), bytes * 8.0 / 1e9, kCacheLine / bytes_per_record};
}

}  // namespace ex
