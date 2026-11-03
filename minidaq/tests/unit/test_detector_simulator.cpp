// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <numeric>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/truth_counter.hpp"

using minidaq::Picoseconds;
using minidaq::ScannerGeometry;
using namespace minidaq::sim;

namespace {

SimulatorConfig point_in_air() {
  SimulatorConfig c;
  c.activity_bq = 1e6;
  c.non_collinearity_fwhm_deg = 0.0;
  return c;
}

SimulatorConfig brain_phantom(double activity_bq) {
  SimulatorConfig c;
  c.activity_bq = activity_bq;
  c.source = {SourceShape::Kind::cylinder, {0, 0, 0}, 80.0, 100.0};
  c.phantom = {90.0, 180.0};
  return c;
}

double stddev(const std::vector<double>& v) {
  const double mean = std::accumulate(v.begin(), v.end(), 0.0) / static_cast<double>(v.size());
  double sq = 0.0;
  for (double x : v) {
    sq += (x - mean) * (x - mean);
  }
  return std::sqrt(sq / static_cast<double>(v.size() - 1));
}

}  // namespace

TEST(DetectorSimulator, RejectsImpossibleConfigurations) {
  // REQ: SRS-SIM-012
  SimulatorConfig c = point_in_air();
  c.activity_bq = 0.0;
  EXPECT_FALSE(validate(c));
  c = point_in_air();
  c.source.centre_mm = {200.0, 0.0, 0.0};  // outside the ring
  EXPECT_FALSE(validate(c));
  c = point_in_air();
  c.phantom = {160.0, 100.0};  // larger than the ring
  EXPECT_FALSE(validate(c));
  c = brain_phantom(1e6);
  c.source.radius_mm = 95.0;  // sticks out of the phantom
  EXPECT_FALSE(validate(c));
  c = point_in_air();
  c.detector.photofraction = 1.5;
  EXPECT_FALSE(validate(c));
  EXPECT_TRUE(validate(brain_phantom(1e6)));
  EXPECT_THROW(DetectorSimulator{c}, std::invalid_argument);
}

TEST(DetectorSimulator, RejectsNaNInEveryNumericField) {
  // REQ: SRS-SIM-012
  // A NaN fails every comparison, so a check written as "x <= 0 is an error"
  // would accept it. Each field is set to NaN on its own.
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const std::vector<void (*)(SimulatorConfig&, double)> fields{
      [](SimulatorConfig& c, double v) { c.activity_bq = v; },
      [](SimulatorConfig& c, double v) { c.source.centre_mm.x = v; },
      [](SimulatorConfig& c, double v) { c.source.centre_mm.z = v; },
      [](SimulatorConfig& c, double v) { c.source.radius_mm = v; },
      [](SimulatorConfig& c, double v) { c.source.length_mm = v; },
      [](SimulatorConfig& c, double v) { c.phantom.radius_mm = v; },
      [](SimulatorConfig& c, double v) { c.phantom.length_mm = v; },
      [](SimulatorConfig& c, double v) { c.detector.crystal_mu_per_mm = v; },
      [](SimulatorConfig& c, double v) { c.detector.photofraction = v; },
      [](SimulatorConfig& c, double v) { c.detector.energy_resolution_fwhm = v; },
      [](SimulatorConfig& c, double v) { c.detector.ctr_fwhm_ps = v; },
      [](SimulatorConfig& c, double v) { c.detector.threshold_kev = v; },
      [](SimulatorConfig& c, double v) { c.non_collinearity_fwhm_deg = v; },
      [](SimulatorConfig& c, double v) { c.detector.gain_spread = v; },
      [](SimulatorConfig& c, double v) { c.detector.saturation_kev = v; },
      [](SimulatorConfig& c, double v) { c.detector.time_skew_ps = v; },
  };
  for (std::size_t i = 0; i < fields.size(); ++i) {
    SimulatorConfig c = brain_phantom(1e6);
    fields[i](c, nan);
    EXPECT_FALSE(validate(c)) << "field " << i;
  }
}

TEST(DetectorSimulator, SameSeedSameStream) {
  // REQ: SRS-SIM-013
  DetectorSimulator a{brain_phantom(5e6)};
  DetectorSimulator b{brain_phantom(5e6)};
  std::vector<TruthSingle> x(20'000);
  std::vector<TruthSingle> y(20'000);
  a.generate(x);
  b.generate(y);
  for (std::size_t i = 0; i < x.size(); ++i) {
    ASSERT_EQ(x[i].single, y[i].single) << i;
    ASSERT_EQ(x[i].decay, y[i].decay) << i;
  }
  SimulatorConfig other = brain_phantom(5e6);
  other.seed = 2;
  DetectorSimulator c{other};
  c.generate(y);
  EXPECT_NE(x[0].single, y[0].single);
}

TEST(DetectorSimulator, OutputIsTimeOrderedAndValid) {
  // REQ: SRS-SIM-014
  DetectorSimulator sim{brain_phantom(20e6)};
  std::vector<TruthSingle> out(100'000);
  sim.generate(out);
  for (std::size_t i = 1; i < out.size(); ++i) {
    ASSERT_LE(out[i - 1].single.time, out[i].single.time) << i;
  }
  for (const auto& s : out) {
    ASSERT_TRUE(ScannerGeometry::valid(s.single.crystal));
    ASSERT_GE(s.single.energy.count(), 100.0F);
  }
}

TEST(DetectorSimulator, DecayRateMatchesActivity) {
  DetectorSimulator sim{point_in_air()};  // 1 MBq
  (void)sim.generate_until(Picoseconds{100'000'000'000});  // 0.1 s
  // Poisson: 100,000 expected, standard deviation 316.
  EXPECT_NEAR(static_cast<double>(sim.stats().decays), 1e5, 1500.0);
}

TEST(DetectorSimulator, AxialAcceptanceOfAPointSource) {
  // REQ: SRS-SIM-015
  // A photon from the centre reaches the crystals if |cos(theta)| < h / sqrt(R^2 + h^2),
  // where h is half the axial length and R the inner radius; isotropic emission
  // makes that fraction equal to the bound itself.
  DetectorSimulator sim{point_in_air()};
  (void)sim.generate_until(Picoseconds{100'000'000'000});
  const auto& st = sim.stats();
  const double h = 0.5 * ScannerGeometry::crystal_rings * ScannerGeometry::axial_pitch_mm;
  const double expected = h / std::hypot(ScannerGeometry::inner_radius_mm, h);
  const double entered = 1.0 - static_cast<double>(st.missed_ring) / static_cast<double>(st.photons);
  EXPECT_NEAR(entered, expected, 0.005);
  EXPECT_EQ(st.scattered_in_phantom, 0U);
}

TEST(DetectorSimulator, EnergyResolutionAt511) {
  // REQ: SRS-SIM-016
  SimulatorConfig c = point_in_air();
  c.detector.photofraction = 1.0;
  c.detector.threshold_kev = 0.0;
  DetectorSimulator sim{c};
  std::vector<TruthSingle> out(100'000);
  sim.generate(out);
  std::vector<double> e;
  for (const auto& s : out) {
    e.push_back(static_cast<double>(s.single.energy.count()));
  }
  const double mean = std::accumulate(e.begin(), e.end(), 0.0) / static_cast<double>(e.size());
  EXPECT_NEAR(mean, 511.0, 1.0);
  EXPECT_NEAR(2.3548 * stddev(e) / 511.0, 0.12, 0.003);
}

TEST(DetectorSimulator, CoincidenceTimeResolution) {
  // REQ: SRS-SIM-017
  // Photons from the centre travel equal distances to the ring; with a very
  // short attenuation length both interact at the crystal face, so the time
  // difference of a true pair has the detector's CTR as its FWHM.
  SimulatorConfig c = point_in_air();
  c.detector.crystal_mu_per_mm = 50.0;
  DetectorSimulator sim{c};
  const auto out = sim.generate_until(Picoseconds{200'000'000'000});
  std::vector<double> dt;
  for (std::size_t i = 0; i + 1 < out.size(); ++i) {
    if (out[i].decay == out[i + 1].decay) {
      const auto& p0 = out[i].photon == 0 ? out[i] : out[i + 1];
      const auto& p1 = out[i].photon == 0 ? out[i + 1] : out[i];
      dt.push_back(static_cast<double>((p1.single.time - p0.single.time).count()));
    }
  }
  ASSERT_GT(dt.size(), 10'000U);
  EXPECT_NEAR(2.3548 * stddev(dt), 300.0, 10.0);
}

TEST(DetectorSimulator, PhantomScattersAndTheEnergyWindowRejectsScatter) {
  // REQ: SRS-SIM-018
  DetectorSimulator sim{brain_phantom(4e6)};
  const auto out = sim.generate_until(Picoseconds{100'000'000'000});
  EXPECT_GT(sim.stats().scattered_in_phantom, 0U);

  const auto wide = count_coincidences(out, {Picoseconds{4'000}, 100.0, 1000.0});
  const auto narrow = count_coincidences(out, {Picoseconds{4'000}, 435.0, 650.0});
  const auto sf = [](const CoincidenceCounts& k) {
    return static_cast<double>(k.scatters) / static_cast<double>(k.trues + k.scatters);
  };
  EXPECT_GT(sf(wide), 0.2);
  EXPECT_LT(sf(narrow), 0.7 * sf(wide));
  // Both photons of a true must deposit their full energy to pass the narrow
  // window, which with a photofraction of 0.6 keeps a bit more than 0.6^2 of them.
  EXPECT_GT(static_cast<double>(narrow.trues), 0.36 * static_cast<double>(wide.trues));

  double e_scattered = 0.0;
  double e_direct = 0.0;
  std::size_t n_scattered = 0;
  std::size_t n_direct = 0;
  for (const auto& s : out) {
    (s.scattered ? e_scattered : e_direct) += static_cast<double>(s.single.energy.count());
    ++(s.scattered ? n_scattered : n_direct);
  }
  EXPECT_LT(e_scattered / static_cast<double>(n_scattered), e_direct / static_cast<double>(n_direct) - 50.0);
}

TEST(DetectorSimulator, TruesAreLinearAndRandomsQuadraticInActivity) {
  // REQ: SRS-SIM-019
  // Deterministic for the seeds, so the tolerances are about 2 standard deviations
  // of the Poisson counts (about 180 randoms at the lower activity).
  const Picoseconds duration{100'000'000'000};  // 0.1 s
  const CountingWindow window{Picoseconds{4'000}, 100.0, 1000.0};
  DetectorSimulator low{brain_phantom(2e6)};
  DetectorSimulator high{brain_phantom(8e6)};
  const auto a = count_coincidences(low.generate_until(duration), window);
  const auto b = count_coincidences(high.generate_until(duration), window);
  const double trues_ratio = static_cast<double>(b.trues) / static_cast<double>(a.trues);
  const double randoms_ratio = static_cast<double>(b.randoms) / static_cast<double>(a.randoms);
  EXPECT_NEAR(trues_ratio, 4.0, 0.3);
  EXPECT_NEAR(randoms_ratio, 16.0, 3.0);
}

namespace {

SimulatorConfig uncalibrated(double gain_spread, double saturation_kev, double skew_ps) {
  SimulatorConfig c = point_in_air();
  c.detector.gain_spread = gain_spread;
  c.detector.saturation_kev = saturation_kev;
  c.detector.time_skew_ps = skew_ps;
  return c;
}

}  // namespace

TEST(DetectorSimulator, RefusesAnUncalibratedDetectorBeyondItsRange) {
  // REQ: SRS-SIM-012
  EXPECT_FALSE(validate(uncalibrated(0.51, 0.0, 0.0)));
  EXPECT_FALSE(validate(uncalibrated(-0.01, 0.0, 0.0)));
  EXPECT_FALSE(validate(uncalibrated(0.0, -1.0, 0.0)));
  EXPECT_FALSE(validate(uncalibrated(0.0, 0.0, 4'001.0)));
  EXPECT_TRUE(validate(uncalibrated(0.5, 1.0e6, 4'000.0)));
}

TEST(DetectorSimulator, AnUncalibratedDetectorReportsEachCrystalsOwnGainAndDelay) {
  // REQ: SRS-SIM-022
  const SimulatorConfig plain = point_in_air();
  const SimulatorConfig raw = uncalibrated(0.1, 4'000.0, 300.0);
  DetectorSimulator a{plain};
  DetectorSimulator b{raw};
  EXPECT_EQ(a.crystal_gains()[0], 1.0);
  EXPECT_EQ(a.crystal_skews_ps()[0], 0.0);

  // The same decays: crystal by crystal, the reported energy is the gain times the saturated
  // energy, and the time is later by the crystal's delay.
  const auto x = a.generate_until(Picoseconds{50'000'000'000});
  const auto y = b.generate_until(Picoseconds{50'000'000'000});
  ASSERT_GT(x.size(), 1'000U);
  // Map each single of b back to its decay and photon to compare.
  std::size_t compared = 0;
  std::size_t j = 0;
  for (const auto& s : x) {
    // b is ordered by its delayed times; find the same decay and photon nearby.
    for (std::size_t k = j > 50 ? j - 50 : 0; k < std::min(y.size(), j + 50); ++k) {
      if (y[k].decay == s.decay && y[k].photon == s.photon) {
        const std::uint32_t c = s.single.crystal.value();
        ASSERT_EQ(y[k].single.crystal, s.single.crystal);
        const double e = static_cast<double>(s.single.energy.count());
        const double want = b.crystal_gains()[c] * 4'000.0 * -std::expm1(-e / 4'000.0);
        EXPECT_NEAR(static_cast<double>(y[k].single.energy.count()), want, 1e-3 * want);
        EXPECT_NEAR(static_cast<double>(y[k].single.time.count() - s.single.time.count()),
                    b.crystal_skews_ps()[c], 1.0);
        ++compared;
        break;
      }
    }
    ++j;
  }
  EXPECT_GT(compared, x.size() * 9 / 10);

  // The crystals' values have the spreads asked for, within their bounds.
  const auto g = b.crystal_gains();
  const auto t = b.crystal_skews_ps();
  const double mean_g = std::accumulate(g.begin(), g.end(), 0.0) / static_cast<double>(g.size());
  double var_g = 0.0;
  double var_t = 0.0;
  for (std::size_t i = 0; i < g.size(); ++i) {
    var_g += (g[i] - mean_g) * (g[i] - mean_g);
    var_t += t[i] * t[i];
    ASSERT_GE(g[i], 0.6);
    ASSERT_LE(g[i], 1.6);
    ASSERT_LE(std::abs(t[i]), 4'000.0);
  }
  EXPECT_NEAR(mean_g, 1.0, 0.005);
  EXPECT_NEAR(std::sqrt(var_g / static_cast<double>(g.size())), 0.1, 0.005);
  EXPECT_NEAR(std::sqrt(var_t / static_cast<double>(t.size())), 300.0, 10.0);
}

TEST(DetectorSimulator, AnUncalibratedDetectorStillDeliversInTimeOrder) {
  // REQ: SRS-SIM-022
  DetectorSimulator sim{uncalibrated(0.1, 0.0, 1'000.0)};
  std::vector<TruthSingle> v(20'000);
  sim.generate(v);
  for (std::size_t i = 1; i < v.size(); ++i) {
    ASSERT_LE(v[i - 1].single.time, v[i].single.time) << i;
  }
}
