#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <span>
#include <string>
#include <vector>

namespace ex {
// Sum of frame durations; returns INT64_MAX if the true sum would overflow.
std::int64_t total_duration_saturating(std::span<const std::int64_t> frames_ps);
// 1 keV bins; values >= 1023 keV go to the top bin.
void fill_energy_histogram(std::array<std::uint32_t, 1024>& hist, std::initializer_list<float> energies_kev);
// Returns the first name, then appends `extra` placeholder names.
std::string label_and_extend(std::vector<std::string>& names, int extra);
// Reads a host-order 64-bit word from any address.
std::uint64_t read_word(const std::byte* p);
// Bit mask with only bit `channel` set, channel in [0, 63].
std::uint64_t channel_mask(unsigned channel);
}  // namespace ex
