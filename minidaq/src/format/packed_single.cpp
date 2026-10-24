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
  std::size_t written = 0;
  for (std::size_t i = 0; i < n; ++i) {
    const Fields f = unpack(words[i]);
    ++stats_.words;
    const Picoseconds t = unwrapper_.unwrap(f.time_code);
    if (f.crystal >= num_crystals_) {
      ++stats_.invalid_crystal;
      continue;
    }
    out[written++] = Single{t, CrystalId{f.crystal}, energy_of(f.energy_code)};
  }
  return written;
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
