// SPDX-License-Identifier: MIT
// minidaq_sim: run the detector simulator, print where the photons went and
// the coincidence counts by truth, optionally write the singles (Chapter 8).
//
//   minidaq_sim --activity 5e6 --seconds 0.5 --phantom 90 --truth singles.csv
#include <algorithm>
#include <cstdio>
#include <memory>
#include <string>
#include <string_view>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "minidaq/sim/truth_counter.hpp"

namespace {

struct FileCloser {
  void operator()(std::FILE* f) const noexcept { (void)std::fclose(f); }  // NOLINT(cppcoreguidelines-owning-memory): owned by the unique_ptr
};
using File = std::unique_ptr<std::FILE, FileCloser>;

constexpr const char* usage =
    "usage: minidaq_sim [--activity BQ] [--seconds S] [--source point|cylinder] [--phantom RADIUS_MM]\n"
    "                   [--window PS] [--elow KEV] [--ehigh KEV] [--ctr PS] [--seed N]\n"
    "                   [--words FILE] [--truth FILE.csv]\n";

double percent(std::uint64_t part, std::uint64_t whole) {
  return whole == 0 ? 0.0 : 100.0 * static_cast<double>(part) / static_cast<double>(whole);
}

}  // namespace

int main(int argc, char** argv) {
  using namespace minidaq::sim;
  SimulatorConfig cfg;
  double seconds = 0.1;
  double phantom_mm = 90.0;
  bool cylinder = true;
  CountingWindow window{minidaq::Picoseconds{4'000}, 435.0, 650.0};
  std::string words_path;
  std::string truth_path;
  for (int i = 1; i < argc; i += 2) {  // every option takes a value
    const std::string_view a{argv[i]};
    const std::string_view v = i + 1 < argc ? argv[i + 1] : "";
    bool ok = true;
    if (a == "--activity") {
      ok = minidaq::parse_into(v, cfg.activity_bq, 1.0, 1e10);
    } else if (a == "--seconds") {
      ok = minidaq::parse_into(v, seconds, 1e-6, 10.0);  // all singles are kept in memory
    } else if (a == "--source") {
      ok = v == "point" || v == "cylinder";
      cylinder = v == "cylinder";
    } else if (a == "--phantom") {
      ok = minidaq::parse_into(v, phantom_mm, 0.0, 140.0);
    } else if (a == "--window") {
      std::int64_t ps = 0;
      ok = minidaq::parse_into(v, ps, std::int64_t{1}, std::int64_t{1'000'000});
      window.width = minidaq::Picoseconds{ps};
    } else if (a == "--elow") {
      ok = minidaq::parse_into(v, window.energy_low_kev, 0.0, 2000.0);
    } else if (a == "--ehigh") {
      ok = minidaq::parse_into(v, window.energy_high_kev, 0.0, 2000.0);
    } else if (a == "--ctr") {
      ok = minidaq::parse_into(v, cfg.detector.ctr_fwhm_ps, 0.0, 10'000.0);
    } else if (a == "--seed") {
      ok = minidaq::parse_into(v, cfg.seed, std::uint64_t{0}, ~std::uint64_t{0});
    } else if (a == "--words" && !v.empty()) {
      words_path = v;
    } else if (a == "--truth" && !v.empty()) {
      truth_path = v;
    } else {
      ok = false;
    }
    if (!ok) {
      std::fputs(usage, stderr);
      return 2;
    }
  }
  if (cylinder) {
    // A brain-sized uniform cylinder inside the water phantom.
    cfg.source = {SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, std::min(80.0, phantom_mm > 0 ? phantom_mm - 10.0 : 80.0),
                  100.0};
  }
  if (phantom_mm > 0.0) {
    cfg.phantom = {phantom_mm, 180.0};
  }
  if (auto v = validate(cfg); !v) {
    std::fprintf(stderr, "minidaq_sim: %s\n", v.error().c_str());
    return 2;
  }

  DetectorSimulator sim{cfg};
  const auto singles = sim.generate_until(minidaq::Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
  const auto& st = sim.stats();
  const auto counts = count_coincidences(singles, window);

  std::printf("decays                %12llu  (%.3g Bq for %.3g s)\n", static_cast<unsigned long long>(st.decays),
              cfg.activity_bq, seconds);
  std::printf("photons               %12llu\n", static_cast<unsigned long long>(st.photons));
  std::printf("  scattered in phantom %11llu  %5.1f%%\n", static_cast<unsigned long long>(st.scattered_in_phantom),
              percent(st.scattered_in_phantom, st.photons));
  std::printf("  left the ring ends   %11llu  %5.1f%%\n", static_cast<unsigned long long>(st.missed_ring),
              percent(st.missed_ring, st.photons));
  std::printf("  passed the crystal   %11llu  %5.1f%%\n", static_cast<unsigned long long>(st.passed_through),
              percent(st.passed_through, st.photons));
  std::printf("  below threshold      %11llu  %5.1f%%\n", static_cast<unsigned long long>(st.below_threshold),
              percent(st.below_threshold, st.photons));
  std::printf("  recorded singles     %11llu  %5.1f%%\n", static_cast<unsigned long long>(st.singles),
              percent(st.singles, st.photons));
  std::printf("window %lld ps, energy %.0f to %.0f keV: %llu singles\n",
              static_cast<long long>(window.width.count()), window.energy_low_kev, window.energy_high_kev,
              static_cast<unsigned long long>(counts.singles));
  std::printf("  trues     %10llu  %8.0f /s\n", static_cast<unsigned long long>(counts.trues),
              static_cast<double>(counts.trues) / seconds);
  std::printf("  scatters  %10llu  %8.0f /s  scatter fraction %.3f\n", static_cast<unsigned long long>(counts.scatters),
              static_cast<double>(counts.scatters) / seconds,
              counts.trues + counts.scatters == 0
                  ? 0.0
                  : static_cast<double>(counts.scatters) / static_cast<double>(counts.trues + counts.scatters));
  std::printf("  randoms   %10llu  %8.0f /s\n", static_cast<unsigned long long>(counts.randoms),
              static_cast<double>(counts.randoms) / seconds);
  std::printf("  multiples %10llu  %8.0f /s\n", static_cast<unsigned long long>(counts.multiples),
              static_cast<double>(counts.multiples) / seconds);

  if (!words_path.empty()) {
    const File f{std::fopen(words_path.c_str(), "wb")};  // NOLINT(cppcoreguidelines-owning-memory): owned by File
    bool ok = f != nullptr;
    for (const auto& s : singles) {
      if (!ok) {
        break;
      }
      const std::uint64_t w = minidaq::packed::encode(s.single);
      unsigned char bytes[8];  // NOLINT(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays): fwrite buffer
      for (int b = 0; b < 8; ++b) {
        bytes[b] = static_cast<unsigned char>(w >> (8 * b));  // little-endian, as on the wire
      }
      ok = std::fwrite(bytes, 1, sizeof bytes, f.get()) == sizeof bytes;
    }
    if (!ok || std::fflush(f.get()) != 0) {
      std::fprintf(stderr, "minidaq_sim: cannot write %s\n", words_path.c_str());
      return 1;
    }
  }
  if (!truth_path.empty()) {
    const File f{std::fopen(truth_path.c_str(), "w")};  // NOLINT(cppcoreguidelines-owning-memory): owned by File
    bool ok = f != nullptr && std::fputs("time_ps,crystal,energy_kev,decay,photon,scattered\n", f.get()) >= 0;
    for (const auto& s : singles) {
      if (!ok) {
        break;
      }
      ok = std::fprintf(f.get(), "%lld,%u,%.2f,%llu,%u,%d\n", static_cast<long long>(s.single.time.count()),
                        s.single.crystal.value(), static_cast<double>(s.single.energy.count()),
                        static_cast<unsigned long long>(s.decay), static_cast<unsigned>(s.photon),
                        s.scattered ? 1 : 0) > 0;
    }
    if (!ok || std::fflush(f.get()) != 0) {
      std::fprintf(stderr, "minidaq_sim: cannot write %s\n", truth_path.c_str());
      return 1;
    }
  }
  return 0;
}
