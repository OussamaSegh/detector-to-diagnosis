// SPDX-License-Identifier: MIT
#include "compton.hpp"

namespace ex84 {

double compton_energy_kev(double e_kev, double cos_theta) {
  return e_kev / (1.0 - (e_kev / electron_rest_energy_kev) * (1.0 - cos_theta));  // TODO: check the sign
}

double sample_cos_theta(double e_kev, std::mt19937_64& rng) {
  (void)e_kev;  // TODO: the angle should depend on the energy
  std::uniform_real_distribution<double> u{-1.0, 1.0};
  return u(rng);
}

}  // namespace ex84
