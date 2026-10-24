// SPDX-License-Identifier: MIT
// Exercise 8.4: Compton kinematics and the Klein-Nishina angular distribution.
#pragma once

#include <random>

namespace ex84 {

inline constexpr double electron_rest_energy_kev = 510.998950;

// Energy after Compton scattering of a photon of energy e_kev through an angle with this cosine.
[[nodiscard]] double compton_energy_kev(double e_kev, double cos_theta);

// cos(theta) of the scattering angle, distributed as the Klein-Nishina cross section.
[[nodiscard]] double sample_cos_theta(double e_kev, std::mt19937_64& rng);

}  // namespace ex84
