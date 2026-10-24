// SPDX-License-Identifier: MIT
#include "compton.hpp"

namespace ex84 {

double compton_energy_kev(double e_kev, double cos_theta) {
  return e_kev / (1.0 + (e_kev / electron_rest_energy_kev) * (1.0 - cos_theta));
}

// [snippet:sample]
// Rejection sampling. Propose cos(theta) uniformly in [-1, 1], which is uniform
// in solid angle, and accept it with probability f / f_max, where
// f = P^2 (P + 1/P - sin^2) is the Klein-Nishina shape. f is largest at
// cos(theta) = 1, where P = 1 and f = 2, at every energy. At 511 keV about 29%
// of the proposals are accepted; each attempt costs two random numbers.
double sample_cos_theta(double e_kev, std::mt19937_64& rng) {
  std::uniform_real_distribution<double> u{0.0, 1.0};
  for (;;) {
    const double c = 2.0 * u(rng) - 1.0;
    const double p = compton_energy_kev(e_kev, c) / e_kev;
    const double f = p * p * (p + 1.0 / p - (1.0 - c * c));
    if (2.0 * u(rng) <= f) {
      return c;
    }
  }
}
// [/snippet:sample]

}  // namespace ex84
