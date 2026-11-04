// SPDX-License-Identifier: MIT
#include "geometry.hpp"

#include <numbers>

namespace rings {

double Geometry::circumference_mm() const {
  return 2.0 * std::numbers::pi * config_.ring_radius_mm;
}

double Geometry::axial_mm(int ring) const { return ring * config_.crystal_pitch_mm; }

}  // namespace rings
