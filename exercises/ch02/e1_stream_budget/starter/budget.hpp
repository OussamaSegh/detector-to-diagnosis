#pragma once
// Exercise 2.1 starter. TODO: fill in the arithmetic.
#include <cstddef>

namespace ex {

struct Budget {
  double bytes_per_s;
  double gib_per_s;   // 1 GiB = 2^30 bytes
  double gbit_per_s;  // 1 Gbit = 10^9 bits (network convention)
  std::size_t records_per_cache_line;
};

constexpr Budget stream_budget(double records_per_s, std::size_t bytes_per_record) {
  (void)records_per_s;
  (void)bytes_per_record;
  return Budget{0, 0, 0, 0};  // TODO
}

}  // namespace ex
