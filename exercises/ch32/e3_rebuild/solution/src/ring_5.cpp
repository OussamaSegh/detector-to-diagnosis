// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_5(const Geometry& g) { return g.axial_mm(5) + g.circumference_mm(); }

}  // namespace rings
