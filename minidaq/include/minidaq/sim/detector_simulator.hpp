// SPDX-License-Identifier: MIT
// MiniDAQ - the detector simulator (Chapter 8).
//
// A Monte Carlo model of positron decays in a source, the two annihilation
// photons, their Compton scattering in a water phantom, and their detection in
// the ring of crystals of ScannerGeometry. The output is what the readout
// would deliver, a time-ordered stream of singles, plus the ground truth for
// each single (which decay, which photon, scattered or not), so that later
// chapters can test a coincidence sorter against what really happened.
//
// It is a teaching model, not a validated physics simulation: Chapter 8's
// model card lists what it leaves out. Use GATE or a similar validated code
// for anything that informs a design decision about the real scanner.
#pragma once

#include <cstdint>
#include <random>
#include <span>
#include <string>
#include <vector>

#include "minidaq/core/expected.hpp"
#include "minidaq/core/single.hpp"
#include "minidaq/sim/physics.hpp"

namespace minidaq::sim {

// [snippet:config]
// Where the activity is. Coordinates in mm, origin at the scanner centre,
// z along the scanner axis.
struct SourceShape {
  enum class Kind : std::uint8_t { point, cylinder };
  Kind kind = Kind::point;
  physics::Vec3 centre_mm{0.0, 0.0, 0.0};
  double radius_mm = 0.0;  // cylinder only: uniform activity inside
  double length_mm = 0.0;  // cylinder only
};

// A water cylinder centred on the scanner axis; radius 0 means none.
struct Phantom {
  double radius_mm = 0.0;
  double length_mm = 0.0;
};

// What the detector does with a photon that reaches it. The defaults are
// typical of a LYSO/SiPM brain scanner (assumption: confirm with team for
// NeuroLF's actual values).
struct DetectorModel {
  double crystal_mu_per_mm = 0.087;     // LYSO at 511 keV, used for all energies
  double photofraction = 0.6;           // interacting photons depositing their full energy
  double energy_resolution_fwhm = 0.12; // FWHM / E at 511 keV, scales as 1/sqrt(E)
  double ctr_fwhm_ps = 300.0;           // coincidence time resolution (pair of singles)
  double threshold_kev = 100.0;         // singles below this are not recorded
};

struct SimulatorConfig {
  double activity_bq = 1.0e6;           // positron decays per second
  SourceShape source{};
  Phantom phantom{};
  DetectorModel detector{};
  double non_collinearity_fwhm_deg = 0.5;  // 0 for exactly back-to-back photons
  std::uint64_t seed = 1;
};
// [/snippet:config]

// Checks a configuration; the message names the first problem found.
[[nodiscard]] Expected<SimulatorConfig, std::string> validate(const SimulatorConfig& cfg);

// [snippet:truth]
// A single and the truth about it.
struct TruthSingle {
  Single single{};
  std::uint64_t decay = 0;  // index of the decay that produced it, from 0
  std::uint8_t photon = 0;  // 0 or 1: which of the two annihilation photons
  bool scattered = false;   // Compton scattered in the phantom at least once
};
// [/snippet:truth]

// Counters for the model card and the tests: where the photons went.
struct SimulatorStats {
  std::uint64_t decays = 0;
  std::uint64_t photons = 0;              // 2 per decay
  std::uint64_t scattered_in_phantom = 0; // photons that scattered at least once
  std::uint64_t absorbed_in_phantom = 0;  // fell below the tracking cut in the phantom
  std::uint64_t missed_ring = 0;          // left through the open ends of the ring
  std::uint64_t passed_through = 0;       // reached a crystal without interacting
  std::uint64_t below_threshold = 0;      // interacted, deposited less than the threshold
  std::uint64_t singles = 0;              // recorded
};

class DetectorSimulator {
 public:
  // Throws std::invalid_argument if validate(cfg) fails.
  explicit DetectorSimulator(const SimulatorConfig& cfg);

  // Fills `out` with the next singles in time order and returns how many it
  // wrote (always out.size(): the source never runs dry).
  std::size_t generate(std::span<TruthSingle> out);

  // All singles with a time before `end` that have not been returned yet, in
  // time order. Convenient for tests and tools; allocates.
  [[nodiscard]] std::vector<TruthSingle> generate_until(Picoseconds end);

  [[nodiscard]] const SimulatorStats& stats() const noexcept { return stats_; }
  [[nodiscard]] const SimulatorConfig& config() const noexcept { return cfg_; }

 private:
  void simulate_next_decay();
  // From point p along unit direction d; both change as the photon scatters.
  void track_photon(physics::Vec3 p, physics::Vec3 d, std::uint8_t photon);
  [[nodiscard]] physics::Vec3 sample_emission_point();
  [[nodiscard]] physics::Vec3 sample_isotropic();
  [[nodiscard]] double sample_klein_nishina_cos(double e_kev);
  [[nodiscard]] bool ready() const noexcept;
  TruthSingle pop();

  SimulatorConfig cfg_;
  std::mt19937_64 rng_;
  std::exponential_distribution<double> decay_gap_ps_;
  std::uniform_real_distribution<double> unit_{0.0, 1.0};
  std::normal_distribution<double> gauss_{0.0, 1.0};
  double time_sigma_ps_;
  double time_clamp_ps_;
  double next_decay_ps_ = 0.0;
  std::uint64_t decay_index_ = 0;
  double current_decay_ps_ = 0.0;
  std::vector<TruthSingle> pending_;  // min-heap on time: singles not yet returned
  SimulatorStats stats_{};
};

}  // namespace minidaq::sim
