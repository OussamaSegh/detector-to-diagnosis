// SPDX-License-Identifier: MIT
#include "bias_controller.hpp"

namespace exercise {

Decision BiasController::step(double temperature_c) {
  // TODO: the readings not believed and the alarm (they latch), the warning with its hysteresis,
  // the law with its limits, and the setpoint to write.
  (void)temperature_c;
  return {};
}

void BiasController::acknowledge() {
  // TODO
}

}  // namespace exercise
