#pragma once
// Exercise 1.3 solution. See NOTES.md.
#include <cstddef>
#include <cstdint>
#include <span>

#include "minidaq/core/expected.hpp"

namespace ex {

struct Single {
  std::int64_t time_ps;
  std::uint32_t crystal;
  float energy_kev;
};

enum class ParseError { truncated, negative_time, crystal_out_of_range, energy_not_finite, energy_out_of_range };

minidaq::Expected<Single, ParseError> parse_single(std::span<const std::byte> bytes) noexcept;

}  // namespace ex
