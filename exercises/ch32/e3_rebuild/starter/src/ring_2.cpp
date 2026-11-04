// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_2(const Geometry& g) { return g.axial_mm(2) + g.circumference_mm(); }

}  // namespace rings
