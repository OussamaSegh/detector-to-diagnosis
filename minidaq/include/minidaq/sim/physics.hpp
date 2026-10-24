// SPDX-License-Identifier: MIT
// MiniDAQ - photon physics used by the detector simulator (Chapter 8).
//
// Only what a 511 keV annihilation photon does on its way from the source to
// a crystal: Compton kinematics, the Klein-Nishina angular distribution,
// attenuation in water, and straight-line geometry. Everything else (positron
// range, photoelectric absorption in tissue, Rayleigh scattering as a
// separate process, scatter inside the detector) is left out and listed in
// Chapter 8's model card.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <optional>

namespace minidaq::sim::physics {

inline constexpr double electron_rest_energy_kev = 510.998950;  // m_e c^2 (CODATA 2018)
inline constexpr double annihilation_energy_kev = electron_rest_energy_kev;
inline constexpr double speed_of_light_mm_per_ps = 0.299792458;
inline constexpr double fwhm_per_sigma = 2.354820045;  // 2 * sqrt(2 ln 2)

struct Vec3 {
  double x;
  double y;
  double z;
};

[[nodiscard]] constexpr Vec3 operator+(const Vec3& a, const Vec3& b) noexcept { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
[[nodiscard]] constexpr Vec3 operator*(double s, const Vec3& v) noexcept { return {s * v.x, s * v.y, s * v.z}; }
[[nodiscard]] constexpr Vec3 operator-(const Vec3& v) noexcept { return {-v.x, -v.y, -v.z}; }
[[nodiscard]] constexpr double dot(const Vec3& a, const Vec3& b) noexcept { return a.x * b.x + a.y * b.y + a.z * b.z; }
[[nodiscard]] inline double norm(const Vec3& v) noexcept { return std::sqrt(dot(v, v)); }

// [snippet:compton]
// Energy of a photon of energy `e_kev` after Compton scattering through an
// angle whose cosine is `cos_theta`.
[[nodiscard]] constexpr double compton_energy_kev(double e_kev, double cos_theta) noexcept {
  return e_kev / (1.0 + (e_kev / electron_rest_energy_kev) * (1.0 - cos_theta));
}

// Klein-Nishina differential cross section per unit solid angle, without the
// constant factor r_e^2 / 2. Its maximum over cos_theta is 2, at cos_theta = 1.
[[nodiscard]] constexpr double klein_nishina_shape(double e_kev, double cos_theta) noexcept {
  const double p = compton_energy_kev(e_kev, cos_theta) / e_kev;  // E'/E
  const double sin2 = 1.0 - cos_theta * cos_theta;
  return p * p * (p + 1.0 / p - sin2);
}
// [/snippet:compton]

// Total mass attenuation coefficient of water, with coherent scattering,
// in cm^2/g (NIST XCOM / Hubbell and Seltzer tables; verify: the table you
// cite in a design document). Interpolated log-log between the points.
struct AttenuationPoint {
  double kev;
  double cm2_per_g;
};
inline constexpr std::array<AttenuationPoint, 7> water_attenuation{{
    {100.0, 0.1707},
    {150.0, 0.1505},
    {200.0, 0.1370},
    {300.0, 0.1186},
    {400.0, 0.1061},
    {500.0, 0.09687},
    {600.0, 0.08956},
}};

// Linear attenuation coefficient of water (density 1 g/cm^3) in 1/mm.
[[nodiscard]] inline double water_mu_per_mm(double e_kev) noexcept {
  const auto& t = water_attenuation;
  const double e = std::clamp(e_kev, t.front().kev, t.back().kev);
  std::size_t i = 1;
  while (i + 1 < t.size() && t[i].kev < e) {
    ++i;
  }
  const auto& a = t[i - 1];
  const auto& b = t[i];
  const double f = std::log(e / a.kev) / std::log(b.kev / a.kev);
  const double mu_cm = std::exp(std::log(a.cm2_per_g) + f * std::log(b.cm2_per_g / a.cm2_per_g));
  return mu_cm / 10.0;
}

// [snippet:cylinder]
// Distance along the unit direction `d` from the point `p` to where the ray
// leaves the infinite cylinder x^2 + y^2 = r^2. `p` must be inside (or on) it.
// Returns nothing for a ray parallel to the axis, which never leaves.
[[nodiscard]] inline std::optional<double> exit_distance_cylinder(const Vec3& p, const Vec3& d, double r) noexcept {
  const double a = d.x * d.x + d.y * d.y;
  if (a < 1e-18) {
    return std::nullopt;
  }
  const double b = p.x * d.x + p.y * d.y;
  const double c = p.x * p.x + p.y * p.y - r * r;  // <= 0 inside
  const double disc = b * b - a * c;
  return (-b + std::sqrt(std::max(disc, 0.0))) / a;
}
// [/snippet:cylinder]

// Distance to leave the slab |z| <= half_length along d (infinite if d.z == 0).
[[nodiscard]] inline double exit_distance_slab(const Vec3& p, const Vec3& d, double half_length) noexcept {
  if (d.z > 0.0) {
    return (half_length - p.z) / d.z;
  }
  if (d.z < 0.0) {
    return (-half_length - p.z) / d.z;
  }
  return std::numeric_limits<double>::infinity();
}

// A unit vector at angle theta (given by its cosine) and azimuth phi from the
// unit vector `d`.
[[nodiscard]] inline Vec3 rotate(const Vec3& d, double cos_theta, double phi) noexcept {
  const double sin_theta = std::sqrt(std::max(0.0, 1.0 - cos_theta * cos_theta));
  const double cp = std::cos(phi);
  const double sp = std::sin(phi);
  // Any unit vector u perpendicular to d, then v = d x u.
  const Vec3 helper = std::abs(d.z) < 0.9 ? Vec3{0.0, 0.0, 1.0} : Vec3{1.0, 0.0, 0.0};
  Vec3 u{helper.y * d.z - helper.z * d.y, helper.z * d.x - helper.x * d.z, helper.x * d.y - helper.y * d.x};
  u = (1.0 / norm(u)) * u;
  const Vec3 v{d.y * u.z - d.z * u.y, d.z * u.x - d.x * u.z, d.x * u.y - d.y * u.x};
  return (cos_theta * d) + (sin_theta * cp) * u + (sin_theta * sp) * v;
}

}  // namespace minidaq::sim::physics
