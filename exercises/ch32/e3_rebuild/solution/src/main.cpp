// SPDX-License-Identifier: MIT
#include <cstdio>

#include "config.hpp"
#include "geometry.hpp"
#include "rings.hpp"

int main() {
  const rings::Geometry g(rings::default_config());
  const double total = rings::ring_0(g) + rings::ring_1(g) + rings::ring_2(g) + rings::ring_3(g) +
                       rings::ring_4(g) + rings::ring_5(g) + rings::ring_6(g) + rings::ring_7(g);
  std::printf("%.3f\n", total);
  return 0;
}
