// SPDX-License-Identifier: MIT
#include "tdc_word.hpp"

namespace ex91 {

// [snippet:decode]
std::optional<Hit> HitDecoder::decode(std::uint64_t word) {
  if ((word >> 60) != type_hit) {
    ++stats_.other_words;  // not a hit: skip it, but count it
    return std::nullopt;
  }
  const auto channel = static_cast<std::uint16_t>((word >> 50) & 0x3FF);
  const std::uint64_t code = word & ((std::uint64_t{1} << time_bits) - 1);  // coarse and fine at once

  // Unwrap with the half-range rule: a step back of more than half the range
  // is a wrap; a smaller step back is a late word from before the latest one.
  constexpr std::uint64_t half = std::uint64_t{1} << (time_bits - 1);
  std::int64_t epoch = epoch_;
  if (!started_) {
    started_ = true;
    last_code_ = code;
  } else if (code < last_code_ && last_code_ - code > half) {
    epoch = ++epoch_;  // wrapped forward
    ++stats_.wraps;
    last_code_ = code;
  } else if (code > last_code_ && code - last_code_ > half) {
    epoch = epoch_ - 1;  // a late word from just before the latest wrap
  } else if (code > last_code_) {
    last_code_ = code;
  }
  ++stats_.hits;
  return Hit{channel, (epoch * wrap_period_ps) + static_cast<std::int64_t>(code) * fine_bin_ps};
}
// [/snippet:decode]

}  // namespace ex91
