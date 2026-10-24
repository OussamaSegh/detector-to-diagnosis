// SPDX-License-Identifier: MIT
#include "tdc_word.hpp"

namespace ex91 {

// TODO(9.1): this decoder passes the happy path and fails the tests that
// matter. Find out why, then fix it:
//  - every word is treated as a hit;
//  - a word that arrives slightly late is taken for a wrap of the counter.
std::optional<Hit> HitDecoder::decode(std::uint64_t word) {
  const auto channel = static_cast<std::uint16_t>((word >> 50) & 0x3FF);
  const std::uint64_t coarse = (word >> 10) & ((std::uint64_t{1} << 40) - 1);
  const std::uint64_t fine = word & 0x3FF;
  const std::uint64_t code = (coarse << 10) | fine;
  if (started_ && code < last_code_) {
    ++epoch_;  // the counter went backwards: it must have wrapped
    ++stats_.wraps;
  }
  started_ = true;
  last_code_ = code;
  ++stats_.hits;
  return Hit{channel, (epoch_ * wrap_period_ps) + static_cast<std::int64_t>(code) * fine_bin_ps};
}

}  // namespace ex91
