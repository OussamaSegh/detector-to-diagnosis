// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_4(const Geometry& g) { return g.axial_mm(4) + g.circumference_mm(); }

}  // namespace rings
