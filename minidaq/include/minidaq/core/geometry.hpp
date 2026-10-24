// SPDX-License-Identifier: MIT
// MiniDAQ - reference scanner geometry, computed at compile time (Chapter 1).
//
// assumption: confirm with team. NeuroLF's real geometry is not public in
// detail. MiniDAQ uses a brain-sized single-ring-of-blocks scanner with
// typical values: 300 mm inner diameter, 24 blocks around the ring, 3 block
// rings axially, 16 x 16 crystals per block, about 2.45 mm crystal pitch.
#pragma once

#include <array>
#include <cstdint>
#include <numbers>

#include "minidaq/core/constexpr_math.hpp"
#include "minidaq/core/ids.hpp"

namespace minidaq {

struct ScannerGeometry {
  static constexpr std::uint32_t crystals_per_block_transaxial = 16;
  static constexpr std::uint32_t crystals_per_block_axial = 16;
  static constexpr std::uint32_t blocks_per_ring = 24;
  static constexpr std::uint32_t block_rings = 3;

  static constexpr std::uint32_t crystals_per_ring = crystals_per_block_transaxial * blocks_per_ring;
  static constexpr std::uint32_t crystal_rings = crystals_per_block_axial * block_rings;
  static constexpr std::uint32_t num_crystals = crystals_per_ring * crystal_rings;
  static constexpr std::uint32_t num_blocks = blocks_per_ring * block_rings;

  static constexpr double inner_radius_mm = 150.0;
  static constexpr double crystal_depth_mm = 15.0;
  static constexpr double axial_pitch_mm = 2.45;
  // Transaxial pitch follows from the ring circumference.
  static constexpr double transaxial_pitch_mm =
      2.0 * std::numbers::pi * inner_radius_mm / static_cast<double>(crystals_per_ring);

  // Crystal id layout: id = ring * crystals_per_ring + transaxial_index.
  [[nodiscard]] static constexpr bool valid(CrystalId c) noexcept {
    return c.value() < num_crystals;
  }
  [[nodiscard]] static constexpr std::uint32_t ring_of(CrystalId c) noexcept {
    return c.value() / crystals_per_ring;
  }
  [[nodiscard]] static constexpr std::uint32_t transaxial_of(CrystalId c) noexcept {
    return c.value() % crystals_per_ring;
  }
  [[nodiscard]] static constexpr std::uint32_t block_of(CrystalId c) noexcept {
    const std::uint32_t block_ring = ring_of(c) / crystals_per_block_axial;
    const std::uint32_t block_in_ring = transaxial_of(c) / crystals_per_block_transaxial;
    return block_ring * blocks_per_ring + block_in_ring;
  }
  [[nodiscard]] static constexpr CrystalId make_crystal(std::uint32_t ring,
                                                        std::uint32_t transaxial) noexcept {
    return CrystalId{ring * crystals_per_ring + transaxial};
  }
};

struct Point2 {
  double x;
  double y;
};

// [snippet:table]
// Centre of the front face of every transaxial crystal position, in mm.
// Built entirely at compile time; the binary contains the finished table.
inline constexpr std::array<Point2, ScannerGeometry::crystals_per_ring> crystal_xy_table = [] {
  std::array<Point2, ScannerGeometry::crystals_per_ring> t{};
  constexpr double step = 2.0 * std::numbers::pi / ScannerGeometry::crystals_per_ring;
  for (std::uint32_t i = 0; i < ScannerGeometry::crystals_per_ring; ++i) {
    // Half-step offset so no crystal sits exactly on an axis.
    const auto sc = cmath::sincos((static_cast<double>(i) + 0.5) * step);
    t[i] = Point2{ScannerGeometry::inner_radius_mm * sc.cos,
                  ScannerGeometry::inner_radius_mm * sc.sin};
  }
  return t;
}();
// [/snippet:table]

[[nodiscard]] constexpr double crystal_z_mm(std::uint32_t ring) noexcept {
  // Axial centre of the scanner is z = 0.
  const double half = static_cast<double>(ScannerGeometry::crystal_rings) / 2.0;
  return (static_cast<double>(ring) + 0.5 - half) * ScannerGeometry::axial_pitch_mm;
}

}  // namespace minidaq
