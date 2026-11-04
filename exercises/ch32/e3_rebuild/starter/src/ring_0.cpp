// SPDX-License-Identifier: MIT
#include "geometry.hpp"
#include "rings.hpp"

namespace rings {

double ring_0(const Geometry& g) { return g.axial_mm(0) + g.circumference_mm(); }

}  // namespace rings
