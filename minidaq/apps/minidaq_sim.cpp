// SPDX-License-Identifier: MIT
// minidaq_sim: run the detector simulator, print where the photons went and
// the coincidence counts by truth, optionally write the singles (Chapter 8).
// Then run the coincidence sorter on the same singles and classify what it
// found with the ground truth (Chapter 10). Optionally apply front-end dead
// time and pile-up first, use a NEMA-style line source, and print one line of
// count rates for scripts (Chapter 11). Optionally write the coincidences to
// MDQ-L1 list-mode files with the sink the DAQ uses (Chapter 12).
//
//   minidaq_sim --activity 5e6 --seconds 0.5 --phantom 90 --truth singles.csv
//   minidaq_sim --activity 20e6 --policy take_winner_of_goods --fov 120
//   minidaq_sim --nema 1 --activity 100e6 --deadtime paralyzable --tau 200 --pileup 1
//   minidaq_sim --source point --centre 40,-25,0 --phantom 0 --fov 120 --listmode out/
#include <algorithm>
#include <exception>
#include <cstdio>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/core/parse_number.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/count_rates.hpp"
#include "minidaq/sim/dead_time.hpp"
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
    "                   [--words FILE] [--truth FILE.csv]\n"
    "                   [--mode fixed|per_single] [--policy NAME] [--delay PS] [--sectors N] [--fov MM]\n"
    "                   [--deadtime none|non_paralyzable|paralyzable] [--tau NS] [--pileup 0|1]\n"
    "                   [--deadtime-unit block|crystal] [--nema 0|1]\n"
    "                   [--centre X,Y,Z] [--listmode DIR] [--max-file-mb N] [--fsync none|close|interval]\n";

double percent(std::uint64_t part, std::uint64_t whole) {
  return whole == 0 ? 0.0 : 100.0 * static_cast<double>(part) / static_cast<double>(whole);
}

// [snippet:classify]
// Runs the sorter on the simulated singles and classifies each coincidence it
// found by looking its two singles up in the ground truth.
minidaq::CountRates print_sorter_report(const minidaq::SorterConfig& cfg,
                                        const std::vector<minidaq::sim::TruthSingle>& truth, double seconds,
                                        std::vector<minidaq::Coincidence>& found) {
  using namespace minidaq;
  std::vector<Single> singles;
  singles.reserve(truth.size());
  // (time, crystal) identifies a single; the simulator does not repeat one.
  std::unordered_map<std::uint64_t, std::size_t> index;
  index.reserve(truth.size());
  const auto key = [](const Single& s) {
    return (static_cast<std::uint64_t>(s.time.count()) << 15U) ^ s.crystal.value();
  };
  std::uint64_t ambiguous = 0;
  for (std::size_t i = 0; i < truth.size(); ++i) {
    singles.push_back(truth[i].single);
    if (!index.emplace(key(truth[i].single), i).second) {
      ++ambiguous;
    }
  }
  CoincidenceSorter sorter{cfg};
  sorter.push(singles, found);
  sorter.flush(found);
  std::uint64_t trues = 0;
  std::uint64_t scatters = 0;
  std::uint64_t randoms = 0;
  for (const Coincidence& c : found) {
    if (c.kind != CoincidenceKind::prompt) {
      continue;
    }
    const auto& a = truth[index.at(key(c.first))];
    const auto& b = truth[index.at(key(c.second))];
    if (a.decay != b.decay) {
      ++randoms;
    } else if (a.scattered || b.scattered) {
      ++scatters;
    } else {
      ++trues;
    }
  }
  // [/snippet:classify]
  const SorterStats& st = sorter.stats();
  const auto rate = [&](std::uint64_t n) { return static_cast<double>(n) / seconds; };
  std::printf("sorter: %s window, %s, delay %lld ps, sectors >= %u apart, fov %.0f mm\n",
              std::string{to_string(cfg.mode)}.c_str(), std::string{to_string(cfg.multiples)}.c_str(),
              static_cast<long long>(cfg.delay.count()), cfg.min_sector_difference, cfg.fov_radius_mm);
  std::printf("  prompts   %10llu  %8.0f /s\n", static_cast<unsigned long long>(st.prompts), rate(st.prompts));
  std::printf("    trues   %10llu  %8.0f /s\n", static_cast<unsigned long long>(trues), rate(trues));
  std::printf("    scatter %10llu  %8.0f /s\n", static_cast<unsigned long long>(scatters), rate(scatters));
  std::printf("    randoms %10llu  %8.0f /s  %5.1f%% of prompts\n", static_cast<unsigned long long>(randoms),
              rate(randoms), percent(randoms, st.prompts));
  std::printf("    from multiples %5llu\n", static_cast<unsigned long long>(st.prompts_from_multiples));
  if (cfg.delay.count() > 0) {
    const double err = randoms == 0 ? 0.0
                                    : 100.0 * (static_cast<double>(st.delayed) - static_cast<double>(randoms)) /
                                          static_cast<double>(randoms);
    std::printf("  delayed   %10llu  %8.0f /s  randoms estimate %+.1f%% from truth\n",
                static_cast<unsigned long long>(st.delayed), rate(st.delayed), err);
  }
  std::printf("  multiple windows %llu (%llu singles), geometry rejected %llu, ambiguous singles %llu\n",
              static_cast<unsigned long long>(st.multiple_windows),
              static_cast<unsigned long long>(st.singles_in_multiples),
              static_cast<unsigned long long>(st.geometry_rejected), static_cast<unsigned long long>(ambiguous));
  return CountRates{.trues = rate(trues), .scatters = rate(scatters), .randoms = rate(randoms)};
}

int run(int argc, char** argv) {
  using namespace minidaq::sim;
  SimulatorConfig cfg;
  double seconds = 0.1;
  double phantom_mm = 90.0;
  bool cylinder = true;
  CountingWindow window{minidaq::Picoseconds{4'000}, 435.0, 650.0};
  std::string words_path;
  std::string truth_path;
  minidaq::SorterConfig sorter;
  DeadTimeConfig dead;
  bool nema = false;
  bool centre_given = false;
  physics::Vec3 centre{0.0, 0.0, 0.0};
  minidaq::config::AcquisitionConfig listmode;  // its output section, and the metadata of the files
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
    } else if (a == "--mode") {
      const auto m = minidaq::parse_window_mode(v);
      ok = m.has_value();
      sorter.mode = ok ? *m : sorter.mode;
    } else if (a == "--policy") {
      const auto p = minidaq::parse_multiples_policy(v);
      ok = p.has_value();
      sorter.multiples = ok ? *p : sorter.multiples;
    } else if (a == "--delay") {
      std::int64_t ps = 0;
      ok = minidaq::parse_into(v, ps, std::int64_t{0}, std::int64_t{1'000'000'000});
      sorter.delay = minidaq::Picoseconds{ps};
    } else if (a == "--sectors") {
      ok = minidaq::parse_into(v, sorter.min_sector_difference, std::uint32_t{0}, std::uint32_t{12});
    } else if (a == "--fov") {
      ok = minidaq::parse_into(v, sorter.fov_radius_mm, 0.0, 149.0);
    } else if (a == "--deadtime") {
      const auto m = parse_dead_time_model(v);
      ok = m.has_value();
      dead.model = ok ? *m : dead.model;
    } else if (a == "--tau") {
      double tau_ns = 0.0;
      ok = minidaq::parse_into(v, tau_ns, 0.0, 100'000.0);
      dead.tau = minidaq::Picoseconds{static_cast<std::int64_t>(tau_ns * 1e3)};
    } else if (a == "--pileup") {
      ok = v == "0" || v == "1";
      dead.pileup = v == "1";
    } else if (a == "--deadtime-unit") {
      ok = v == "block" || v == "crystal";
      dead.unit = v == "crystal" ? DeadTimeUnit::crystal : DeadTimeUnit::block;
    } else if (a == "--nema") {
      ok = v == "0" || v == "1";
      nema = v == "1";
    } else if (a == "--centre") {
      // x,y,z in mm
      const auto c1 = v.find(',');
      const auto c2 = c1 == std::string_view::npos ? c1 : v.find(',', c1 + 1);
      ok = c2 != std::string_view::npos && minidaq::parse_into(v.substr(0, c1), centre.x, -140.0, 140.0) &&
           minidaq::parse_into(v.substr(c1 + 1, c2 - c1 - 1), centre.y, -140.0, 140.0) &&
           minidaq::parse_into(v.substr(c2 + 1), centre.z, -100.0, 100.0);
      centre_given = true;
    } else if (a == "--listmode" && !v.empty()) {
      listmode.output.type = "listmode";
      listmode.output.directory = v;
    } else if (a == "--max-file-mb") {
      ok = minidaq::parse_into(v, listmode.output.max_file_mb, std::uint64_t{1}, std::uint64_t{1} << 20);
    } else if (a == "--fsync") {
      ok = v == "none" || v == "close" || v == "interval";
      listmode.output.fsync = v;
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
  if (centre_given) {
    cfg.source.centre_mm = centre;
  }
  if (nema) {
    // NEMA NU 2-style count-rate phantom: a 203 mm diameter, 700 mm long
    // cylinder with a line source 45 mm off the axis (verify: the dimensions
    // against the NU 2 edition in use). Our water stands in for polyethylene,
    // and most of the 700 mm lie outside this short scanner's axial field of
    // view, as they would in a brain scanner.
    cfg.phantom = {101.5, 700.0};
    cfg.source = {SourceShape::Kind::cylinder, {0.0, -45.0, 0.0}, 1.6, 700.0};
  }
  if (auto v = validate(dead); !v) {
    std::fprintf(stderr, "minidaq_sim: %s\n", v.error().c_str());
    return 2;
  }
  if (auto v = validate(cfg); !v) {
    std::fprintf(stderr, "minidaq_sim: %s\n", v.error().c_str());
    return 2;
  }
  sorter.window = window.width;
  sorter.energy_low_kev = window.energy_low_kev;
  sorter.energy_high_kev = window.energy_high_kev;
  if (auto v = minidaq::validate(sorter); !v) {
    std::fprintf(stderr, "minidaq_sim: sorter: %s\n", v.error().c_str());
    return 2;
  }

  DetectorSimulator sim{cfg};
  const auto generated = sim.generate_until(minidaq::Picoseconds{static_cast<std::int64_t>(seconds * 1e12)});
  DeadTime front_end{dead};
  std::vector<TruthSingle> singles;
  singles.reserve(generated.size());
  front_end.push(generated, singles);
  front_end.flush(singles);
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
  if (dead.model != DeadTimeModel::none) {
    const auto& d = front_end.stats();
    std::printf("dead time %s per %s, %.0f ns%s: %llu lost (%.1f%%), %llu piled up\n",
                std::string{to_string(dead.model)}.c_str(), dead.unit == DeadTimeUnit::block ? "block" : "crystal",
                static_cast<double>(dead.tau.count()) / 1e3, dead.pileup ? ", pile-up" : "",
                static_cast<unsigned long long>(d.lost), percent(d.lost, d.singles_in),
                static_cast<unsigned long long>(d.piled_up));
  }
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

  std::vector<minidaq::Coincidence> found;
  const minidaq::CountRates r = print_sorter_report(sorter, singles, seconds, found);
  // One line for scripts (measurements/ch11/countrate.py): rates per second.
  std::printf("countrate activity=%.6g singles=%.6g trues=%.6g scatters=%.6g randoms=%.6g sf=%.4f necr1=%.6g necr2=%.6g\n",
              cfg.activity_bq, static_cast<double>(singles.size()) / seconds, r.trues, r.scatters, r.randoms,
              r.scatter_fraction(), r.necr(1.0), r.necr(2.0));

  if (listmode.output.type == "listmode") {
    // The metadata records the sorter that made these coincidences.
    listmode.description = "minidaq_sim";
    listmode.pipeline.coincidence_window_ps = sorter.window.count();
    listmode.sorter.delay_ps = sorter.delay.count();
    listmode.sorter.energy_low_kev = sorter.energy_low_kev;
    listmode.sorter.energy_high_kev = sorter.energy_high_kev;
    listmode.sorter.fov_radius_mm = sorter.fov_radius_mm;
    listmode.sorter.min_sector_difference = sorter.min_sector_difference;
    std::string error;
    auto sink = minidaq::control::make_listmode_sink(listmode, error);
    if (!sink) {
      std::fprintf(stderr, "minidaq_sim: %s\n", error.c_str());
      return 1;
    }
    for (std::size_t i = 0; i < found.size(); i += 4096) {
      sink->write(std::span{found}.subspan(i, std::min<std::size_t>(4096, found.size() - i)));
    }
    // The run record: what was simulated and the truth behind the records,
    // which no measured run has.
    const nlohmann::json record = {
        {"simulation",
         {{"program", "minidaq_sim"},
          {"activity_bq", cfg.activity_bq},
          {"seconds", seconds},
          {"seed", cfg.seed},
          {"truth", {{"trues", counts.trues}, {"scatters", counts.scatters}, {"randoms", counts.randoms},
                     {"multiples", counts.multiples}}},
          {"sorter_rates_per_s", {{"trues", r.trues}, {"scatters", r.scatters}, {"randoms", r.randoms}}}}}};
    if (auto e = sink->close(record.dump())) {
      std::fprintf(stderr, "minidaq_sim: %s\n", e->c_str());
      return 1;
    }
    std::printf("list mode: %s\n", sink->describe().c_str());
    for (const auto& c : sink->counters()) {
      if (c.name == "coincidences" || c.name == "files" || c.name == "bytes") {
        std::printf("  %s %llu\n", c.name.c_str(), static_cast<unsigned long long>(c.value));
      }
    }
  }
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

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {  // e.g. std::bad_alloc, or JSON with invalid UTF-8
    std::fprintf(stderr, "minidaq_sim: %s\n", e.what());
    return 2;
  }
}
