// Exercise F2.3, starter: this works, but it is eager: it decodes the whole buffer into a vector
// before the caller sees the first single. Rewrite both functions as coroutines that co_yield
// one single at a time, so that a caller who stops after three singles decodes three records.
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include <stdexcept>
#include <vector>

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

inline Single decode(std::span<const std::byte> rec, std::size_t& decoded) {
  Single s;
  std::memcpy(&s, rec.data(), record_size);
  ++decoded;
  if (s.time_ps < 0) throw std::runtime_error{"negative time in record"};
  return s;
}

inline Generator<Single> singles_in(std::span<const std::byte> bytes, std::size_t& decoded) {
  std::vector<Single> all;  // TODO: no vector; co_yield each single as it is decoded
  for (std::size_t off = 0; off + record_size <= bytes.size(); off += record_size) {
    all.push_back(decode(bytes.subspan(off, record_size), decoded));
  }
  for (const Single& s : all) co_yield s;
}

inline Generator<Single> in_window(Generator<Single> in, float lo, float hi) {
  std::vector<Single> kept;  // TODO: no vector; co_yield each single in the window
  for (const Single& s : in) {
    if (s.energy_kev >= lo && s.energy_kev <= hi) kept.push_back(s);
  }
  for (const Single& s : kept) co_yield s;
}

}  // namespace ex
