// SPDX-License-Identifier: MIT
// Exercise 9.1: decoding a TDC hit word with a coarse/fine timestamp.
//
// A made-up front-end format, close in spirit to real TDC ASICs:
//
//  63   60 59        50 49                              10 9        0
// +-------+------------+----------------------------------+----------+
// | type  | channel    | coarse (40 bits)                 | fine (10)|
// +-------+------------+----------------------------------+----------+
//
//  type     0x1: hit. Other values are other word kinds (not hits).
//  channel  0 .. 1023
//  coarse   counts a 195.3125 MHz clock: one tick is 5120 ps
//  fine     interpolates within a tick: 1024 bins of 5 ps (ideal; real fine
//           bins are uneven and need a calibration)
//
// Time code = coarse * 1024 + fine, in 5 ps units. It wraps every 2^40 coarse
// ticks = 2^40 * 5.12 ns = 5629.5 s, about 94 minutes: inside a long scan.
#pragma once

#include <cstdint>
#include <optional>

namespace ex91 {

inline constexpr std::uint64_t type_hit = 0x1;
inline constexpr std::int64_t fine_bin_ps = 5;
inline constexpr std::int64_t coarse_tick_ps = 5120;
inline constexpr unsigned time_bits = 50;                              // coarse and fine together
inline constexpr std::int64_t wrap_period_ps = fine_bin_ps << time_bits;  // 5629.5 s

struct Hit {
  std::uint16_t channel;
  std::int64_t time_ps;  // absolute: wraps already undone
};

struct DecoderStats {
  std::uint64_t hits = 0;
  std::uint64_t other_words = 0;  // words of another type, not decoded
  std::uint64_t wraps = 0;        // times the counter wrapped
};

// Builds a hit word (for tests and simulators).
[[nodiscard]] constexpr std::uint64_t make_hit(std::uint16_t channel, std::uint64_t coarse, std::uint64_t fine) {
  return (type_hit << 60) | ((std::uint64_t{channel} & 0x3FF) << 50) | ((coarse & ((std::uint64_t{1} << 40) - 1)) << 10) |
         (fine & 0x3FF);
}

// Decodes a stream of words in arrival order. Words are time-ordered except
// that a word may arrive up to a few microseconds late (it was buffered in
// another FIFO of the ASIC); far less than half a wrap period.
class HitDecoder {
 public:
  // The hit in `word`, or nothing if it is not a hit word.
  [[nodiscard]] std::optional<Hit> decode(std::uint64_t word);
  [[nodiscard]] const DecoderStats& stats() const noexcept { return stats_; }

 private:
  DecoderStats stats_;
  std::uint64_t last_code_ = 0;  // the latest time code seen
  std::int64_t epoch_ = 0;       // wraps so far
  bool started_ = false;
};

}  // namespace ex91
