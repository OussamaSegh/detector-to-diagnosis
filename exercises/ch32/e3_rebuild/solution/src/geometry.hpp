// SPDX-License-Identifier: MIT
// Exercise 32.3, solution: the geometry keeps the two numbers it needs, and its header names the
// configuration only by a declaration. A file that includes it no longer depends on config.hpp.
#pragma once

namespace rings {

struct Config;

class Geometry {
 public:
  explicit Geometry(const Config& config);
  [[nodiscard]] double circumference_mm() const;
  [[nodiscard]] double axial_mm(int ring) const;

 private:
  double ring_radius_mm_;
  double crystal_pitch_mm_;
};

}  // namespace rings
