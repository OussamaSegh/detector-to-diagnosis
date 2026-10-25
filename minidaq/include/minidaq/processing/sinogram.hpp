// SPDX-License-Identifier: MIT
// MiniDAQ - from coincidences to sinograms (Chapter 12).
//
// A sinogram counts coincidences per line of response (LOR), indexed by the
// LOR's angle (view) and its signed distance from the axis (radial bin). For
// MiniDAQ's ring of N = 384 crystals a LOR between transaxial crystals i < j
// has its normal at angle (i + j + 1) * pi / N and lies at distance
// R * |cos(pi * (j - i) / N)| from the axis. Two neighboring angles are
// combined into one view (the usual interleaving), which gives N / 2 = 192
// views of 0 .. 180 degrees and radial bins at half the crystal pitch near the
// center. Radial positions are not arc-corrected: bin r lies at
// s = -R * sin(pi * r / N).
//
// Axially, a LOR joins crystal rings ring_a and ring_b. Single-slice rebinning
// (SSRB) puts it in slice ring_a + ring_b, 2 * 48 - 1 = 95 slices half a ring
// apart, if |ring_a - ring_b| <= max_ring_difference. The Michelogram counts
// every ring pair before that cut.
//
// With time of flight (TOF), each LOR is also binned by tau = t_a - t_b, the
// arrival time at its endpoint a minus that at b; the annihilation is then
// c * tau / 2 from the LOR's midpoint, towards b. Which endpoint is a is fixed
// per bin (see LorBin), so tau means the same thing for every count in a bin.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/core/single.hpp"

namespace minidaq::sino {

inline constexpr std::uint32_t crystals_per_ring = ScannerGeometry::crystals_per_ring;
inline constexpr std::uint32_t num_views = crystals_per_ring / 2;                          // 192
inline constexpr std::uint32_t num_rings = ScannerGeometry::crystal_rings;                 // 48
inline constexpr std::uint32_t num_ssrb_slices = 2 * num_rings - 1;                        // 95
inline constexpr double speed_of_light_mm_per_ps = 0.299792458;

// [snippet:lorbin]
// Where one LOR goes. `a_is_lower` says which crystal is endpoint a: the one
// with the lower transaxial index unless the bin's angle wrapped past 180
// degrees, which swaps the two ends (and the sign of the radial position).
struct LorBin {
  std::uint32_t view = 0;  // 0 .. num_views - 1
  std::int32_t radial = 0;  // r: the bin is at s = -R sin(pi r / N)
  bool a_is_lower = true;
};

// The bin of the LOR between two transaxial positions, or nullopt if they are
// the same position (an axial line with no transaxial angle).
[[nodiscard]] constexpr std::optional<LorBin> lor_bin(std::uint32_t t1, std::uint32_t t2) noexcept {
  if (t1 == t2) {
    return std::nullopt;
  }
  const std::uint32_t i = t1 < t2 ? t1 : t2;
  const std::uint32_t j = t1 < t2 ? t2 : t1;
  std::uint32_t k = i + j + 1;  // twice the normal angle, in units of pi / N
  std::uint32_t d = j - i;
  const bool wrapped = k >= crystals_per_ring;
  if (wrapped) {  // the same line seen from the opposite side: angle - 180 degrees, s -> -s
    k -= crystals_per_ring;
    d = crystals_per_ring - d;
  }
  return LorBin{k / 2, static_cast<std::int32_t>(d) - static_cast<std::int32_t>(crystals_per_ring / 2), !wrapped};
}
// [/snippet:lorbin]

// The distance from the axis of radial bin r, in mm (not arc-corrected).
[[nodiscard]] double radial_position_mm(std::int32_t r) noexcept;

// The largest |r| whose LORs pass within fov_radius_mm of the axis.
[[nodiscard]] std::int32_t max_radial_bin(double fov_radius_mm) noexcept;

// [snippet:config]
struct SinogramConfig {
  double fov_radius_mm = 120.0;           // LORs farther from the axis are not binned
  std::uint32_t max_ring_difference = 47;  // SSRB cut; 47 keeps every ring pair
  std::uint32_t tof_bins = 1;             // 1: no TOF
  std::int64_t tof_bin_ps = 0;            // width of a TOF bin in tau; required if tof_bins > 1
  std::int64_t delayed_window_ps = 100'000;  // the sorter's delay, removed from a delayed pair's dt
};
// [/snippet:config]

[[nodiscard]] Expected<SinogramConfig, std::string> validate(const SinogramConfig& c);

// [snippet:stats]
struct SinogramStats {
  std::uint64_t prompts = 0;           // prompt coincidences binned
  std::uint64_t delayeds = 0;          // delayed coincidences binned
  std::uint64_t outside_fov = 0;       // LOR farther than fov_radius_mm from the axis
  std::uint64_t ring_difference = 0;   // |ring_a - ring_b| above the cut
  std::uint64_t tof_outside = 0;       // tau beyond the outermost TOF bin
  std::uint64_t no_angle = 0;          // both crystals at the same transaxial position
  std::uint64_t invalid_crystal = 0;   // a crystal id outside the scanner
};
// [/snippet:stats]

// [snippet:placement]
// Where one coincidence goes, or why it goes nowhere. The fields are filled
// as far as the binning got: ring_a and ring_b are valid from ring_difference
// on, tof only for binned.
enum class Outcome : std::uint8_t { binned, invalid_crystal, no_angle, outside_fov, ring_difference, tof_outside };

struct Placement {
  Outcome outcome = Outcome::invalid_crystal;
  std::uint32_t view = 0;
  std::int32_t radial = 0;
  std::uint32_t ring_a = 0;
  std::uint32_t ring_b = 0;
  std::uint32_t tof = 0;
  std::int64_t tau_ps = 0;  // t_a - t_b, the delay removed from a delayed pair
};
// [/snippet:placement]

// Histograms coincidences into SSRB sinograms, prompts and delayeds apart,
// and into a Michelogram of prompts. Memory: tof_bins * 95 * 192 * radial
// bins counts of 4 bytes, twice (16.6 MB per TOF bin at the default FOV).
class Histogrammer {
 public:
  explicit Histogrammer(const SinogramConfig& c);  // c must pass validate()

  // Where c would go; add() is locate() and one increment.
  [[nodiscard]] Placement locate(const Coincidence& c) const noexcept;
  void add(const Coincidence& c) noexcept;
  void add(std::span<const Coincidence> cs) noexcept {
    for (const auto& c : cs) {
      add(c);
    }
  }

  [[nodiscard]] const SinogramConfig& config() const noexcept { return cfg_; }
  [[nodiscard]] std::int32_t max_radial() const noexcept { return max_r_; }
  [[nodiscard]] std::uint32_t radial_bins() const noexcept { return static_cast<std::uint32_t>(2 * max_r_ + 1); }
  [[nodiscard]] std::size_t bins_per_tof() const noexcept {
    return std::size_t{num_ssrb_slices} * num_views * radial_bins();
  }

  // Flat index of (tof, slice, view, radial r), radial fastest. Layout of the
  // arrays below and of the files written by write_interfile().
  [[nodiscard]] std::size_t index(std::uint32_t tof, std::uint32_t slice, std::uint32_t view,
                                  std::int32_t r) const noexcept;

  [[nodiscard]] const std::vector<std::uint32_t>& prompts() const noexcept { return prompts_; }
  [[nodiscard]] const std::vector<std::uint32_t>& delayeds() const noexcept { return delayeds_; }
  // michelogram()[ring_a * 48 + ring_b]: prompts inside the FOV by the rings
  // of endpoints a and b, before the ring-difference cut. Not symmetric:
  // (ring_a, ring_b) and (ring_b, ring_a) are LORs tilted the opposite ways.
  [[nodiscard]] const std::vector<std::uint64_t>& michelogram() const noexcept { return michelogram_; }
  [[nodiscard]] const SinogramStats& stats() const noexcept { return stats_; }

  // The 2D sinogram of all slices and TOF bins added up: views * radial bins.
  [[nodiscard]] std::vector<std::uint64_t> collapsed(bool delayed = false) const;

 private:
  SinogramConfig cfg_;
  std::int32_t max_r_;
  std::vector<std::uint32_t> prompts_;
  std::vector<std::uint32_t> delayeds_;
  std::vector<std::uint64_t> michelogram_;
  SinogramStats stats_;
};

// An Interfile-style "key := value" text header that says how to read the
// two data files: little-endian uint32 in index() order, prompts and
// delayeds. Writing the files is the caller's business (the core does no I/O).
[[nodiscard]] std::string interfile_header(const Histogrammer& h, std::string_view prompts_file,
                                           std::string_view delayeds_file, std::string_view comment);

}  // namespace minidaq::sino
