// SPDX-License-Identifier: MIT
// Exercise 22.2: one slow-control cycle for one board's SiPM bias.
#pragma once

#include <optional>

namespace exercise {

struct BiasSettings {
  double vbd_25c_mv = 38'000.0;  // breakdown voltage at 25 C
  double k_mv_per_c = 34.0;      // its temperature coefficient
  double vov_mv = 2'700.0;       // the overvoltage to keep
  double min_mv = 36'000.0;      // never set a bias outside these limits
  double max_mv = 43'000.0;
  double step_mv = 5.0;  // write again only when the bias moved this much
  double warning_c = 35.0;
  double hysteresis_c = 1.0;
  double alarm_c = 40.0;
  double min_c = 5.0;  // below: the reading is not believed
};

enum class Level { normal, warning, alarm, invalid };

struct Decision {
  bool bias_on = false;
  std::optional<double> write_mv;  // a setpoint to write now, in whole millivolts
  double target_mv = 0;            // after the limits
  bool at_limit = false;
  Level level = Level::normal;
};

class BiasController {
 public:
  explicit BiasController(BiasSettings s = {}) : s_{s} {}
  Decision step(double temperature_c);
  void acknowledge();
  [[nodiscard]] bool latched() const { return latched_.has_value(); }

 private:
  BiasSettings s_;
  std::optional<Level> latched_;  // alarm or invalid while latched
  std::optional<double>
      written_mv_;  // the last setpoint written since the start or the acknowledgment
  Level warning_ = Level::normal;  // normal or warning: the state of the hysteresis
};

}  // namespace exercise
