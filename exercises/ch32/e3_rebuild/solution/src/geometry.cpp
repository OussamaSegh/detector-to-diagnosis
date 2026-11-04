// SPDX-License-Identifier: MIT
#include "geometry.hpp"

#include <numbers>

#include "config.hpp"

namespace rings {

Geometry::Geometry(const Config& config)
    : ring_radius_mm_(config.ring_radius_mm), crystal_pitch_mm_(config.crystal_pitch_mm) {}

double Geometry::circumference_mm() const { return 2.0 * std::numbers::pi * ring_radius_mm_; }

double Geometry::axial_mm(int ring) const { return ring * crystal_pitch_mm_; }

}  // namespace rings
