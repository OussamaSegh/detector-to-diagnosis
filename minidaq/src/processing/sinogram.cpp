// SPDX-License-Identifier: MIT
#include "minidaq/processing/sinogram.hpp"

#include <cmath>
#include <numbers>
#include <sstream>

namespace minidaq::sino {

double radial_position_mm(std::int32_t r) noexcept {
  return -ScannerGeometry::inner_radius_mm *
         std::sin(std::numbers::pi * static_cast<double>(r) / static_cast<double>(crystals_per_ring));
}

std::int32_t max_radial_bin(double fov_radius_mm) noexcept {
  const double x = std::min(fov_radius_mm / ScannerGeometry::inner_radius_mm, 1.0);
  const auto r = static_cast<std::int32_t>(std::floor(std::asin(x) * static_cast<double>(crystals_per_ring) /
                                                      std::numbers::pi));
  return std::min(r, static_cast<std::int32_t>(crystals_per_ring / 2) - 1);
}

Expected<SinogramConfig, std::string> validate(const SinogramConfig& c) {
  if (!(c.fov_radius_mm > 0.0) || !(c.fov_radius_mm < ScannerGeometry::inner_radius_mm)) {
    return Unexpected<std::string>{"fov_radius_mm must be in (0, ring radius)"};
  }
  if (c.max_ring_difference >= num_rings) {
    return Unexpected<std::string>{"max_ring_difference must be at most 47"};
  }
  if (c.tof_bins == 0 || c.tof_bins > 255) {
    return Unexpected<std::string>{"tof_bins must be in 1 .. 255"};
  }
  if (c.tof_bins > 1 && c.tof_bin_ps <= 0) {
    return Unexpected<std::string>{"tof_bin_ps must be positive when tof_bins > 1"};
  }
  if (c.delayed_window_ps < 0) {
    return Unexpected<std::string>{"delayed_window_ps must not be negative"};
  }
  return c;
}

Histogrammer::Histogrammer(const SinogramConfig& c)
    : cfg_{c},
      max_r_{max_radial_bin(c.fov_radius_mm)},
      prompts_(std::size_t{c.tof_bins} * bins_per_tof(), 0),
      delayeds_(prompts_.size(), 0),
      michelogram_(std::size_t{num_rings} * num_rings, 0) {}

std::size_t Histogrammer::index(std::uint32_t tof, std::uint32_t slice, std::uint32_t view,
                                std::int32_t r) const noexcept {
  return ((std::size_t{tof} * num_ssrb_slices + slice) * num_views + view) * radial_bins() +
         static_cast<std::size_t>(r + max_r_);
}

// [snippet:locate]
Placement Histogrammer::locate(const Coincidence& c) const noexcept {
  Placement p;
  if (!ScannerGeometry::valid(c.first.crystal) || !ScannerGeometry::valid(c.second.crystal)) {
    return p;
  }
  const auto t1 = ScannerGeometry::transaxial_of(c.first.crystal);
  const auto t2 = ScannerGeometry::transaxial_of(c.second.crystal);
  const auto bin = lor_bin(t1, t2);
  if (!bin) {
    p.outcome = Outcome::no_angle;
    return p;
  }
  p.view = bin->view;
  p.radial = bin->radial;
  if (bin->radial < -max_r_ || bin->radial > max_r_) {
    p.outcome = Outcome::outside_fov;
    return p;
  }
  // Is the earlier single (first) at endpoint a?
  const bool first_is_a = (t1 < t2) == bin->a_is_lower;
  const auto ring_first = ScannerGeometry::ring_of(c.first.crystal);
  const auto ring_second = ScannerGeometry::ring_of(c.second.crystal);
  p.ring_a = first_is_a ? ring_first : ring_second;
  p.ring_b = first_is_a ? ring_second : ring_first;
  if ((p.ring_a > p.ring_b ? p.ring_a - p.ring_b : p.ring_b - p.ring_a) > cfg_.max_ring_difference) {
    p.outcome = Outcome::ring_difference;
    return p;
  }
  // dt = t_second - t_first; tau = t_a - t_b. A delayed pair's second single
  // was taken one delay later, so the delay comes off first.
  const bool delayed = c.kind == CoincidenceKind::delayed;
  const std::int64_t dt = c.time_difference().count() - (delayed ? cfg_.delayed_window_ps : 0);
  p.tau_ps = first_is_a ? -dt : dt;
  if (cfg_.tof_bins > 1) {
    // Bins of width w, centered on tau = 0 when tof_bins is odd: bin = floor((2 tau + n w) / 2w).
    const std::int64_t w = cfg_.tof_bin_ps;
    const std::int64_t num = 2 * p.tau_ps + std::int64_t{cfg_.tof_bins} * w;
    if (num < 0 || num / (2 * w) >= std::int64_t{cfg_.tof_bins}) {
      p.outcome = Outcome::tof_outside;
      return p;
    }
    p.tof = static_cast<std::uint32_t>(num / (2 * w));
  }
  p.outcome = Outcome::binned;
  return p;
}
// [/snippet:locate]

// [snippet:add]
void Histogrammer::add(const Coincidence& c) noexcept {
  const auto p = locate(c);
  const bool delayed = c.kind == CoincidenceKind::delayed;
  if (!delayed && (p.outcome == Outcome::binned || p.outcome == Outcome::ring_difference)) {
    ++michelogram_[std::size_t{p.ring_a} * num_rings + p.ring_b];
  }
  switch (p.outcome) {
    case Outcome::invalid_crystal: ++stats_.invalid_crystal; return;
    case Outcome::no_angle: ++stats_.no_angle; return;
    case Outcome::outside_fov: ++stats_.outside_fov; return;
    case Outcome::ring_difference: ++stats_.ring_difference; return;
    case Outcome::tof_outside: ++stats_.tof_outside; return;
    case Outcome::binned: break;
  }
  const auto i = index(p.tof, p.ring_a + p.ring_b, p.view, p.radial);
  if (delayed) {
    ++delayeds_[i];
    ++stats_.delayeds;
  } else {
    ++prompts_[i];
    ++stats_.prompts;
  }
}
// [/snippet:add]

std::vector<std::uint64_t> Histogrammer::collapsed(bool delayed) const {
  const auto& src = delayed ? delayeds_ : prompts_;
  const std::size_t plane = std::size_t{num_views} * radial_bins();
  std::vector<std::uint64_t> out(plane, 0);
  for (std::size_t i = 0; i < src.size(); ++i) {
    out[i % plane] += src[i];
  }
  return out;
}

std::string interfile_header(const Histogrammer& h, std::string_view prompts_file, std::string_view delayeds_file,
                             std::string_view comment) {
  const auto& c = h.config();
  const auto& s = h.stats();
  std::ostringstream o;
  o << "!INTERFILE :=\n"
    << "; MiniDAQ SSRB sinograms (Chapter 12). The keys follow the Interfile style but are\n"
    << "; MiniDAQ's own: they say how to read the data, not how STIR or CASToR would.\n"
    << "originating system := MiniDAQ\n"
    << "comment := " << comment << "\n"
    << "prompts data file := " << prompts_file << "\n"
    << "delayeds data file := " << delayeds_file << "\n"
    << "number format := unsigned integer\n"
    << "number of bytes per pixel := 4\n"
    << "imagedata byte order := LITTLEENDIAN\n"
    << "number of dimensions := 4\n"
    << "matrix axes order := tof, slice, view, radial (radial fastest)\n"
    << "matrix size [radial] := " << h.radial_bins() << "\n"
    << "matrix size [view] := " << num_views << "\n"
    << "matrix size [slice] := " << num_ssrb_slices << "\n"
    << "matrix size [tof] := " << c.tof_bins << "\n"
    << "first radial bin r := " << -h.max_radial() << "\n"
    << "radial positions := not arc-corrected, s(r) = -R sin(pi r / N) mm\n"
    << "view angles := view v holds the normals at angles 2v * pi / N and (2v + 1) * pi / N\n"
    << "crystals per ring N := " << crystals_per_ring << "\n"
    << "ring radius R (mm) := " << ScannerGeometry::inner_radius_mm << "\n"
    << "number of rings := " << num_rings << "\n"
    << "slice spacing (mm) := " << ScannerGeometry::axial_pitch_mm / 2.0 << "\n"
    << "rebinning := SSRB, slice = ring_a + ring_b\n"
    << "maximum ring difference := " << c.max_ring_difference << "\n"
    << "fov radius (mm) := " << c.fov_radius_mm << "\n"
    << "tof bin width (ps) := " << c.tof_bin_ps << "\n"
    << "tof variable := tau = t_a - t_b, bins centered on 0\n"
    << "prompts binned := " << s.prompts << "\n"
    << "delayeds binned := " << s.delayeds << "\n"
    << "outside fov := " << s.outside_fov << "\n"
    << "above ring difference := " << s.ring_difference << "\n"
    << "tof outside := " << s.tof_outside << "\n"
    << "!END OF INTERFILE :=\n";
  return o.str();
}

}  // namespace minidaq::sino
