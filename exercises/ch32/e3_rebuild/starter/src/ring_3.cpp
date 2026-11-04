// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_3(const Geometry& g) { return g.axial_mm(3) + g.circumference_mm(); }

}  // namespace rings
