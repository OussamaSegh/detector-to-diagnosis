// Exercise F2.3, solution: singles read from a list-mode buffer one at a time, on demand.
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include <stdexcept>

#include "generator.hpp"

namespace ex {

struct Single {
  std::int64_t time_ps = 0;
  std::uint32_t crystal = 0;
  float energy_kev = 0.0F;
  friend bool operator==(const Single&, const Single&) = default;
};
static_assert(sizeof(Single) == 16);

inline constexpr std::size_t record_size = sizeof(Single);

// Decodes one record; counts every decode in `decoded`, so a test can see laziness.
inline Single decode(std::span<const std::byte> rec, std::size_t& decoded) {
  Single s;
  std::memcpy(&s, rec.data(), record_size);
  ++decoded;
  if (s.time_ps < 0) throw std::runtime_error{"negative time in record"};
  return s;
}

// [snippet:singles]
inline Generator<Single> singles_in(std::span<const std::byte> bytes, std::size_t& decoded) {
  for (std::size_t off = 0; off + record_size <= bytes.size(); off += record_size) {
    co_yield decode(bytes.subspan(off, record_size), decoded);  // one record per request
  }
  // A truncated record at the end is not a single: the loop condition leaves it out.
}

inline Generator<Single> in_window(Generator<Single> in, float lo, float hi) {
  for (const Single& s : in) {
    if (s.energy_kev >= lo && s.energy_kev <= hi) co_yield s;
  }
}
// [/snippet:singles]

}  // namespace ex
