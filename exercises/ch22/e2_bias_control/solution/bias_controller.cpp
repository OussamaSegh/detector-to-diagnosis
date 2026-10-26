// SPDX-License-Identifier: MIT
#include "bias_controller.hpp"

#include <algorithm>
#include <cmath>

namespace exercise {

Decision BiasController::step(double temperature_c) {
  Decision d;
  // NaN compares false with everything, so test for it by name: `t < min_c` alone lets it through.
  if (!latched_ && (std::isnan(temperature_c) || temperature_c < s_.min_c)) {
    latched_ = Level::invalid;
  } else if (!latched_ && temperature_c >= s_.alarm_c) {
    latched_ = Level::alarm;
  }
  if (latched_) {
    d.level = *latched_;
    return d;  // bias off, nothing to write, until acknowledged
  }

  if (temperature_c >= s_.warning_c) {
    warning_ = Level::warning;
  } else if (temperature_c < s_.warning_c - s_.hysteresis_c) {
    warning_ = Level::normal;
  }  // in between: as it was
  d.level = warning_;

  const double wanted = s_.vbd_25c_mv + s_.k_mv_per_c * (temperature_c - 25.0) + s_.vov_mv;
  d.target_mv = std::clamp(wanted, s_.min_mv, s_.max_mv);
  d.at_limit = d.target_mv != wanted;
  d.bias_on = true;
  const double rounded = std::round(d.target_mv);
  if (!written_mv_ || std::abs(rounded - *written_mv_) >= s_.step_mv) {
    d.write_mv = rounded;
    written_mv_ = rounded;
  }
  return d;
}

void BiasController::acknowledge() {
  latched_.reset();
  written_mv_.reset();  // the supply was switched off: write the setpoint again
  warning_ = Level::normal;
}

}  // namespace exercise
