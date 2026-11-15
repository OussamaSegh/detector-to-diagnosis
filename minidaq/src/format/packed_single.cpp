// SPDX-License-Identifier: MIT
#include "minidaq/format/packed_single.hpp"

#include <cmath>
#include <cstring>

#include "minidaq/core/bits.hpp"

namespace minidaq::packed {

std::uint64_t encode(const Single& s) noexcept {
  const auto time_code = static_cast<std::uint64_t>(s.time.count() / time_lsb_ps) & time_mask;
  const float e = s.energy.count();
  std::uint32_t energy_code = 0;
  if (e >= energy_max_kev) {
    energy_code = static_cast<std::uint32_t>(energy_mask);
  } else if (e > 0.0F) {  // false for NaN and negatives
    energy_code = static_cast<std::uint32_t>(std::lround(e / energy_lsb_kev));
  }
  return pack(Fields{s.crystal.value(), energy_code, time_code});
}

// [snippet:decode]
std::size_t StreamDecoder::decode(std::span<const std::uint64_t> words, std::span<Single> out) noexcept {
  const std::size_t n = words.size() < out.size() ? words.size() : out.size();
  // Local copies: a store through `out` may alias a member (a Single holds a uint32_t too), so
  // the loop would reload and store the members for every word (MDQ-PR-070).
  TimeUnwrapper unwrapper = unwrapper_;
  const std::uint32_t num_crystals = num_crystals_;
  std::size_t written = 0;
  for (std::size_t i = 0; i < n; ++i) {
    const Fields f = unpack(words[i]);
    const Picoseconds t = unwrapper.unwrap(f.time_code);
    if (f.crystal >= num_crystals) {
      not_a_single(f.crystal, f.energy_code, t);  // a marker or an invalid crystal
      continue;
    }
    out[written++] = Single{t, CrystalId{f.crystal}, energy_of(f.energy_code)};
  }
  unwrapper_ = unwrapper;
  stats_.words += n;
  return written;
}

// Off the loop, so that a single costs what it cost before markers existed: one comparison
// (MDQ-PR-070). The marker's crystal is never below the crystal count.
void StreamDecoder::not_a_single(std::uint32_t crystal, std::uint32_t energy_code,
                                 Picoseconds t) noexcept {
  if (crystal == marker_crystal && energy_code == marker_energy_code) {
    ++stats_.markers;  // a promise, not a single (Chapter 24)
    if (!has_marker_ || t > marker_) {
      marker_ = t;
    }
    has_marker_ = true;
  } else {
    ++stats_.invalid_crystal;
  }
}
// [/snippet:decode]

std::size_t StreamDecoder::decode_bytes(std::span<const std::byte> bytes, std::span<Single> out) noexcept {
  const std::size_t nwords = bytes.size() / sizeof(std::uint64_t);
  truncated_bytes_ += bytes.size() % sizeof(std::uint64_t);
  const std::size_t n = nwords < out.size() ? nwords : out.size();
  std::size_t written = 0;
  for (std::size_t i = 0; i < n; ++i) {
    std::uint64_t w = 0;
    std::memcpy(&w, bytes.data() + i * sizeof w, sizeof w);
    w = from_little_endian(w);
    written += decode(std::span<const std::uint64_t>(&w, 1), out.subspan(written, 1));
  }
  return written;
}

}  // namespace minidaq::packed
