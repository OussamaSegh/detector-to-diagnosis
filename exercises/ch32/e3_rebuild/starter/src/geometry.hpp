// SPDX-License-Identifier: MIT
// Exercise 32.3, starter: every file that uses the geometry also includes the configuration.
#pragma once

#include "config.hpp"

namespace rings {

class Geometry {
 public:
  explicit Geometry(const Config& config) : config_(config) {}
  [[nodiscard]] double circumference_mm() const;
  [[nodiscard]] double axial_mm(int ring) const;

 private:
  Config config_;
};

}  // namespace rings
