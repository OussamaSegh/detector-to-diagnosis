// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_6(const Geometry& g) { return g.axial_mm(6) + g.circumference_mm(); }

}  // namespace rings
