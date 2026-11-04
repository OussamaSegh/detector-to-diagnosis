// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_7(const Geometry& g) { return g.axial_mm(7) + g.circumference_mm(); }

}  // namespace rings
