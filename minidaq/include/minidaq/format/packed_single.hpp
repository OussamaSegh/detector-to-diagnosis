// SPDX-License-Identifier: MIT
// MiniDAQ - the packed 64-bit single word, format MDQ-P1 (Chapter 2).
//
//  63            49 48         38 37                 10 9          0
// +----------------+-------------+---------------------+------------+
// | crystal (15)   | energy (11) | coarse time (28)    | fine (10)  |
// +----------------+-------------+---------------------+------------+
//
//  crystal  global crystal id, 0 .. 32767 (MiniDAQ uses 0 .. 18431)
//  energy   0.5 keV per LSB, 0 .. 1023.5 keV; larger energies saturate at 2047
//  time     38-bit counter of 5 ps units: coarse ticks of 5.12 ns (1024 fine
//           bins of 5 ps each). The counter wraps every 2^38 * 5 ps = 1.374 s;
//           StreamDecoder reconstructs absolute time across wraps.
//
// Words are stored and transmitted little-endian. Field extraction uses shifts
// and masks, never C++ bit-fields, because bit-field layout is
// implementation-defined and cannot describe a wire format portably.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>

#include "minidaq/core/single.hpp"

namespace minidaq::packed {

// [snippet:layout]
inline constexpr unsigned crystal_bits = 15;
inline constexpr unsigned energy_bits = 11;
inline constexpr unsigned time_bits = 38;
inline constexpr unsigned fine_bits = 10;
static_assert(crystal_bits + energy_bits + time_bits == 64);

inline constexpr unsigned time_shift = 0;
inline constexpr unsigned energy_shift = time_bits;
inline constexpr unsigned crystal_shift = time_bits + energy_bits;

inline constexpr std::uint64_t time_mask = (std::uint64_t{1} << time_bits) - 1;
inline constexpr std::uint64_t energy_mask = (std::uint64_t{1} << energy_bits) - 1;
inline constexpr std::uint64_t crystal_mask = (std::uint64_t{1} << crystal_bits) - 1;

inline constexpr std::int64_t time_lsb_ps = 5;
inline constexpr std::int64_t coarse_tick_ps = time_lsb_ps << fine_bits;  // 5120 ps
inline constexpr std::int64_t wrap_period_ps = time_lsb_ps << time_bits;  // 1.374 s
inline constexpr float energy_lsb_kev = 0.5F;
inline constexpr float energy_max_kev = static_cast<float>(energy_mask) * energy_lsb_kev;
// [/snippet:layout]

struct Fields {
  std::uint32_t crystal;
  std::uint32_t energy_code;
  std::uint64_t time_code;
};

// [snippet:codec]
[[nodiscard]] constexpr std::uint64_t pack(Fields f) noexcept {
  return ((std::uint64_t{f.crystal} & crystal_mask) << crystal_shift) |
         ((std::uint64_t{f.energy_code} & energy_mask) << energy_shift) |
         ((f.time_code & time_mask) << time_shift);
}

[[nodiscard]] constexpr Fields unpack(std::uint64_t w) noexcept {
  return Fields{static_cast<std::uint32_t>((w >> crystal_shift) & crystal_mask),
                static_cast<std::uint32_t>((w >> energy_shift) & energy_mask),
                (w >> time_shift) & time_mask};
}

[[nodiscard]] constexpr std::uint64_t coarse_of(std::uint64_t time_code) noexcept {
  return time_code >> fine_bits;
}
[[nodiscard]] constexpr std::uint64_t fine_of(std::uint64_t time_code) noexcept {
  return time_code & ((std::uint64_t{1} << fine_bits) - 1);
}
// [/snippet:codec]

// Encodes a Single. Time is truncated to 5 ps and taken modulo the wrap period
// (precondition: time >= 0). Energy is rounded to 0.5 keV and saturates; NaN
// and negative energies encode as 0. The crystal id must be < 2^15.
[[nodiscard]] std::uint64_t encode(const Single& s) noexcept;

// Decodes the energy code back to keV.
[[nodiscard]] constexpr KeV energy_of(std::uint32_t energy_code) noexcept {
  return KeV{static_cast<float>(energy_code) * energy_lsb_kev};
}

// [snippet:unwrap]
// Reconstructs absolute time from the wrapping 38-bit counter. Assumes the
// stream is time-ordered to within half a wrap period (0.69 s), which every
// real readout guarantees by a large margin.
class TimeUnwrapper {
 public:
  constexpr TimeUnwrapper() noexcept = default;
  // Starting epoch, for streams that begin after one or more wraps.
  constexpr explicit TimeUnwrapper(std::int64_t epoch) noexcept : epoch_{epoch} {}

  [[nodiscard]] constexpr Picoseconds unwrap(std::uint64_t time_code) noexcept {
    constexpr std::uint64_t half = std::uint64_t{1} << (time_bits - 1);
    std::int64_t epoch = epoch_;
    if (has_last_) {
      if (time_code < last_ && last_ - time_code > half) {
        epoch = ++epoch_;  // counter wrapped forward
        last_ = time_code;
      } else if (time_code > last_ && time_code - last_ > half) {
        epoch = epoch_ - 1;  // a slightly late word from before the wrap
      } else if (time_code > last_) {
        last_ = time_code;
      }
    } else {
      last_ = time_code;
      has_last_ = true;
    }
    return Picoseconds{(epoch * wrap_period_ps) + static_cast<std::int64_t>(time_code) * time_lsb_ps};
  }
  [[nodiscard]] constexpr std::int64_t epoch() const noexcept { return epoch_; }

 private:
  std::int64_t epoch_{0};
  std::uint64_t last_{0};
  bool has_last_{false};
};
// [/snippet:unwrap]

struct DecodeStats {
  std::uint64_t words = 0;
  std::uint64_t invalid_crystal = 0;
};

// Zero-allocation stream decoder: decodes words into caller-provided storage.
class StreamDecoder {
 public:
  explicit StreamDecoder(std::uint32_t num_crystals) noexcept : num_crystals_{num_crystals} {}

  // Decodes min(words.size(), out.size()) words; words with an invalid crystal
  // id are counted and skipped. Returns the number of singles written.
  std::size_t decode(std::span<const std::uint64_t> words, std::span<Single> out) noexcept;

  // Same, from little-endian bytes (size must be a multiple of 8; a trailing
  // partial word is ignored and counted as truncated).
  std::size_t decode_bytes(std::span<const std::byte> bytes, std::span<Single> out) noexcept;

  [[nodiscard]] const DecodeStats& stats() const noexcept { return stats_; }
  [[nodiscard]] std::uint64_t truncated_bytes() const noexcept { return truncated_bytes_; }

 private:
  TimeUnwrapper unwrapper_;
  DecodeStats stats_;
  std::uint64_t truncated_bytes_ = 0;
  std::uint32_t num_crystals_;
};

}  // namespace minidaq::packed
