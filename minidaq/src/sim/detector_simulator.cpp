// SPDX-License-Identifier: MIT
#include "minidaq/sim/detector_simulator.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>

#include "minidaq/core/geometry.hpp"

namespace minidaq::sim {

namespace {

using physics::Vec3;
using G = ScannerGeometry;

constexpr double two_pi = 2.0 * std::numbers::pi;
constexpr double ring_half_length_mm = 0.5 * G::crystal_rings * G::axial_pitch_mm;
// Photons below this energy are no longer tracked in the phantom: they would
// be far below any detector threshold.
constexpr double tracking_cut_kev = 50.0;
constexpr int max_phantom_interactions = 20;

bool later(const TruthSingle& a, const TruthSingle& b) noexcept {
  return a.single.time > b.single.time;  // min-heap on time
}

// The checks below are written as "not (valid)" so that a NaN, for which every
// comparison is false, is rejected; "x <= 0.0" would let it through.
bool positive(double x) noexcept { return x > 0.0; }
bool in_range(double x, double lo, double hi) noexcept { return x >= lo && x <= hi; }

}  // namespace

Expected<SimulatorConfig, std::string> validate(const SimulatorConfig& cfg) {
  const auto fail = [](std::string msg) { return Unexpected<std::string>{std::move(msg)}; };
  if (!positive(cfg.activity_bq) || !(cfg.activity_bq <= 1e10)) {
    return fail("activity_bq must be in (0, 1e10]");
  }
  const auto& s = cfg.source;
  const double s_xy = std::hypot(s.centre_mm.x, s.centre_mm.y);
  const double s_radius = s.kind == SourceShape::Kind::cylinder ? s.radius_mm : 0.0;
  const double s_half = s.kind == SourceShape::Kind::cylinder ? 0.5 * s.length_mm : 0.0;
  if (s.kind == SourceShape::Kind::cylinder && (!positive(s.radius_mm) || !positive(s.length_mm))) {
    return fail("a cylinder source needs radius_mm > 0 and length_mm > 0");
  }
  if (!(s_xy + s_radius < G::inner_radius_mm) || !std::isfinite(s.centre_mm.z)) {
    return fail("the source must lie inside the detector ring");
  }
  const auto& p = cfg.phantom;
  if (!in_range(p.radius_mm, 0.0, G::inner_radius_mm) || p.radius_mm == G::inner_radius_mm || !(p.length_mm >= 0.0)) {
    return fail("the phantom radius must be in [0, inner radius of the ring)");
  }
  if (p.radius_mm > 0.0) {
    if (!positive(p.length_mm)) {
      return fail("a phantom needs length_mm > 0");
    }
    if (s_xy + s_radius > p.radius_mm || std::abs(s.centre_mm.z) + s_half > 0.5 * p.length_mm) {
      return fail("the source must lie inside the phantom");
    }
  }
  const auto& d = cfg.detector;
  const bool detector_ok = positive(d.crystal_mu_per_mm) && in_range(d.photofraction, 0.0, 1.0) &&
                           in_range(d.energy_resolution_fwhm, 0.0, 1.0) && d.energy_resolution_fwhm < 1.0 &&
                           d.ctr_fwhm_ps >= 0.0 && d.threshold_kev >= 0.0;
  if (!detector_ok) {
    return fail("detector model out of range (mu > 0, photofraction in [0, 1], resolution in [0, 1), ctr and threshold >= 0)");
  }
  if (!in_range(cfg.non_collinearity_fwhm_deg, 0.0, 10.0) || cfg.non_collinearity_fwhm_deg == 10.0) {
    return fail("non_collinearity_fwhm_deg must be in [0, 10)");
  }
  return cfg;
}

DetectorSimulator::DetectorSimulator(const SimulatorConfig& cfg)
    : cfg_{[&] {
        auto v = validate(cfg);
        if (!v) {
          throw std::invalid_argument("DetectorSimulator: " + v.error());
        }
        return *v;
      }()},
      rng_{cfg.seed},
      decay_gap_ps_{cfg.activity_bq * 1e-12},
      // Each single gets half of the pair's time variance.
      time_sigma_ps_{cfg.detector.ctr_fwhm_ps / (physics::fwhm_per_sigma * std::numbers::sqrt2)},
      time_clamp_ps_{6.0 * time_sigma_ps_},
      next_decay_ps_{decay_gap_ps_(rng_)} {}

// [snippet:order]
// A single can be returned once no future decay can produce an earlier one.
// Flight times are positive, and the time blur is clamped to +-6 sigma, so a
// decay at time t produces singles no earlier than t - time_clamp_ps_.
bool DetectorSimulator::ready() const noexcept {
  return !pending_.empty() &&
         static_cast<double>(pending_.front().single.time.count()) < std::floor(next_decay_ps_ - time_clamp_ps_);
}
// [/snippet:order]

TruthSingle DetectorSimulator::pop() {
  std::pop_heap(pending_.begin(), pending_.end(), later);
  TruthSingle s = pending_.back();
  pending_.pop_back();
  return s;
}

std::size_t DetectorSimulator::generate(std::span<TruthSingle> out) {
  for (auto& s : out) {
    while (!ready()) {
      simulate_next_decay();
    }
    s = pop();
  }
  return out.size();
}

std::vector<TruthSingle> DetectorSimulator::generate_until(Picoseconds end) {
  std::vector<TruthSingle> result;
  for (;;) {
    while (!ready()) {
      simulate_next_decay();
    }
    if (pending_.front().single.time >= end) {
      return result;
    }
    result.push_back(pop());
  }
}

Vec3 DetectorSimulator::sample_isotropic() {
  const double cos_theta = 2.0 * unit_(rng_) - 1.0;
  const double sin_theta = std::sqrt(1.0 - cos_theta * cos_theta);
  const double phi = two_pi * unit_(rng_);
  return {sin_theta * std::cos(phi), sin_theta * std::sin(phi), cos_theta};
}

Vec3 DetectorSimulator::sample_emission_point() {
  const auto& s = cfg_.source;
  if (s.kind == SourceShape::Kind::point) {
    return s.centre_mm;
  }
  const double r = s.radius_mm * std::sqrt(unit_(rng_));  // uniform over the disc
  const double phi = two_pi * unit_(rng_);
  const double z = (unit_(rng_) - 0.5) * s.length_mm;
  return s.centre_mm + Vec3{r * std::cos(phi), r * std::sin(phi), z};
}

// [snippet:kn]
// Rejection sampling: propose cos(theta) uniformly (uniform in solid angle),
// accept with probability shape / 2, since the shape never exceeds 2.
double DetectorSimulator::sample_klein_nishina_cos(double e_kev) {
  for (;;) {
    const double c = 2.0 * unit_(rng_) - 1.0;
    if (2.0 * unit_(rng_) <= physics::klein_nishina_shape(e_kev, c)) {
      return c;
    }
  }
}
// [/snippet:kn]

void DetectorSimulator::simulate_next_decay() {
  current_decay_ps_ = next_decay_ps_;
  decay_index_ = stats_.decays++;
  next_decay_ps_ += decay_gap_ps_(rng_);

  const Vec3 origin = sample_emission_point();
  const Vec3 d1 = sample_isotropic();
  Vec3 d2 = -d1;
  if (cfg_.non_collinearity_fwhm_deg > 0.0) {
    // Deviation from 180 degrees: Gaussian in each of two perpendicular planes.
    const double sigma = cfg_.non_collinearity_fwhm_deg * std::numbers::pi / 180.0 / physics::fwhm_per_sigma;
    const double a = sigma * gauss_(rng_);
    const double b = sigma * gauss_(rng_);
    d2 = physics::rotate(d2, std::cos(std::hypot(a, b)), std::atan2(b, a));
  }
  track_photon(origin, d1, 0);
  track_photon(origin, d2, 1);
}

// [snippet:track]
void DetectorSimulator::track_photon(Vec3 p, Vec3 d, std::uint8_t photon) {
  ++stats_.photons;
  double e = physics::annihilation_energy_kev;
  double path_mm = 0.0;
  bool scattered = false;

  // 1. Through the water phantom: exponential free paths, Compton scatter.
  if (cfg_.phantom.radius_mm > 0.0) {
    for (int i = 0; i < max_phantom_interactions; ++i) {
      const double to_side = physics::exit_distance_cylinder(p, d, cfg_.phantom.radius_mm).value_or(std::numeric_limits<double>::infinity());
      const double to_exit = std::min(to_side, physics::exit_distance_slab(p, d, 0.5 * cfg_.phantom.length_mm));
      const double free_path = -std::log1p(-unit_(rng_)) / physics::water_mu_per_mm(e);
      if (free_path >= to_exit) {
        p = p + to_exit * d;
        path_mm += to_exit;
        break;
      }
      p = p + free_path * d;
      path_mm += free_path;
      const double c = sample_klein_nishina_cos(e);
      e = physics::compton_energy_kev(e, c);
      d = physics::rotate(d, c, two_pi * unit_(rng_));
      scattered = true;
      if (e < tracking_cut_kev) {
        ++stats_.absorbed_in_phantom;
        ++stats_.scattered_in_phantom;
        return;
      }
    }
  }
  if (scattered) {
    ++stats_.scattered_in_phantom;
  }

  // 2. To the inner face of the ring; photons through the open ends are lost.
  const auto to_ring = physics::exit_distance_cylinder(p, d, G::inner_radius_mm);
  if (!to_ring) {
    ++stats_.missed_ring;
    return;
  }
  const Vec3 entry = p + *to_ring * d;
  if (std::abs(entry.z) > ring_half_length_mm) {
    ++stats_.missed_ring;
    return;
  }

  // 3. Into the crystal: interaction depth is exponential; it may pass through.
  const double in_crystal =
      std::min(physics::exit_distance_cylinder(entry, d, G::inner_radius_mm + G::crystal_depth_mm).value_or(0.0),
               physics::exit_distance_slab(entry, d, ring_half_length_mm));
  const double depth = -std::log1p(-unit_(rng_)) / cfg_.detector.crystal_mu_per_mm;
  if (depth >= in_crystal) {
    ++stats_.passed_through;
    return;
  }
  const Vec3 hit = entry + depth * d;
  path_mm += *to_ring + depth;

  // The crystal is the one containing the interaction point, not the entry
  // point: a photon entering at an angle is assigned deeper along its path
  // (parallax error).
  double angle = std::atan2(hit.y, hit.x);
  if (angle < 0.0) {
    angle += two_pi;
  }
  const auto transaxial = static_cast<std::uint32_t>(angle / (two_pi / G::crystals_per_ring)) % G::crystals_per_ring;
  const double ring_f = hit.z / G::axial_pitch_mm + 0.5 * G::crystal_rings;
  const auto ring = static_cast<std::uint32_t>(std::clamp(ring_f, 0.0, static_cast<double>(G::crystal_rings - 1)));

  // 4. Energy: full absorption, or one Compton interaction whose photon escapes.
  double deposit = e;
  if (unit_(rng_) >= cfg_.detector.photofraction) {
    deposit = e - physics::compton_energy_kev(e, sample_klein_nishina_cos(e));
  }
  const double e_sigma = cfg_.detector.energy_resolution_fwhm *
                         std::sqrt(physics::annihilation_energy_kev * deposit) / physics::fwhm_per_sigma;
  const double measured = deposit + e_sigma * gauss_(rng_);
  if (measured < cfg_.detector.threshold_kev) {
    ++stats_.below_threshold;
    return;
  }

  // 5. Time: decay time, flight time, and the detector's time blur.
  const double blur = std::clamp(time_sigma_ps_ * gauss_(rng_), -time_clamp_ps_, time_clamp_ps_);
  const double t = current_decay_ps_ + path_mm / physics::speed_of_light_mm_per_ps + blur;

  TruthSingle s;
  s.single = Single{Picoseconds{std::llround(t)}, G::make_crystal(ring, transaxial), KeV{static_cast<float>(measured)}};
  s.decay = decay_index_;
  s.photon = photon;
  s.scattered = scattered;
  pending_.push_back(s);
  std::push_heap(pending_.begin(), pending_.end(), later);
  ++stats_.singles;
}
// [/snippet:track]

}  // namespace minidaq::sim
