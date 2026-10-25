// SPDX-License-Identifier: MIT
// minidaq_listmode: look into, check and histogram MDQ-L1 list-mode files
// (Chapter 12).
//
//   minidaq_listmode info run-0000.mdql           what is in the file, and is it complete
//   minidaq_listmode verify run-*.mdql            exit 0 only if every block is intact and the run ends
//   minidaq_listmode sino --out s run-*.mdql      SSRB sinograms and a Michelogram
//   minidaq_listmode sino --out s --tof-bins 13 --tof-bin-ps 100 --mrd 10 run-*.mdql
//   minidaq_listmode info run-0000.mdql.part      after a crash: what can be recovered
//
// Files are read whole into memory; a 1 GiB file needs 1 GiB of RAM (a
// production tool would map it instead).
#include <algorithm>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iterator>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/format/list_mode.hpp"
#include "minidaq/processing/sinogram.hpp"

namespace {

using namespace minidaq;
namespace lm = minidaq::listmode;

constexpr const char* usage =
    "usage: minidaq_listmode info FILE...\n"
    "       minidaq_listmode verify FILE...\n"
    "       minidaq_listmode sino --out PREFIX [--fov MM] [--mrd N] [--tof-bins N --tof-bin-ps PS] FILE...\n";

std::vector<std::byte> read_file(const std::string& path) {
  std::ifstream in{path, std::ios::binary};
  if (!in) {
    throw std::runtime_error{"cannot open " + path};
  }
  const std::vector<char> raw{std::istreambuf_iterator<char>{in}, std::istreambuf_iterator<char>{}};
  std::vector<std::byte> out(raw.size());
  std::transform(raw.begin(), raw.end(), out.begin(), [](char c) { return static_cast<std::byte>(c); });
  return out;
}

struct Summary {
  lm::ReaderStats stats;
  std::vector<lm::ReadIssue> issues;
  std::uint64_t prompts = 0;
  std::uint64_t delayeds = 0;
  std::uint64_t tags = 0;
  std::int64_t first_ps = 0;
  std::int64_t last_ps = 0;
  std::uint64_t time_resets = 0;  // a block that starts before the previous block's last record
};

// Walks every block; calls on_event for each coincidence.
template <typename F>
Summary walk(lm::Reader& r, const F& on_event) {
  Summary s;
  bool any = false;
  lm::BlockView b;
  while (r.next(b)) {
    for (std::size_t i = 0; i < b.record_count(); ++i) {
      const auto rec = lm::decode_record(b, i);
      const std::int64_t t = rec.is_tag ? rec.tag.time.count() : rec.event.first.time.count();
      if (!any) {
        s.first_ps = t;
        any = true;
      } else if (i == 0 && t < s.last_ps) {
        ++s.time_resets;
      }
      s.last_ps = std::max(s.last_ps, t);
      if (rec.is_tag) {
        ++s.tags;
        continue;
      }
      ++(rec.event.kind == CoincidenceKind::delayed ? s.delayeds : s.prompts);
      on_event(rec.event);
    }
  }
  s.stats = r.stats();
  s.issues = r.issues();
  return s;
}

void print_issues(const std::vector<lm::ReadIssue>& issues) {
  for (const auto& i : issues) {
    std::printf("  issue at byte %zu: %s\n", i.offset, std::string{lm::to_string(i.error)}.c_str());
  }
}

int info(const std::vector<std::string>& files) {
  int status = 0;
  for (const auto& f : files) {
    const auto bytes = read_file(f);
    lm::Reader r{bytes};
    std::printf("%s: %zu bytes\n", f.c_str(), bytes.size());
    if (!r.header()) {
      std::printf("  not readable: file header %s\n", std::string{lm::to_string(r.header().error())}.c_str());
      status = 1;
      continue;
    }
    std::printf("  MDQ-L1 version %u.%u, header %zu bytes\n", r.header()->major, r.header()->minor,
                r.header()->header_bytes);
    const auto meta = nlohmann::json::parse(r.header()->metadata, nullptr, /*allow_exceptions=*/false);
    std::printf("  metadata: %s\n", meta.is_discarded() ? "(not valid JSON)" : meta.dump(2).c_str());
    const auto s = walk(r, [](const Coincidence&) {});
    const double span_s = static_cast<double>(s.last_ps - s.first_ps) * 1e-12;
    std::printf("  blocks %llu, records %llu: prompts %llu, delayeds %llu, tags %llu\n",
                static_cast<unsigned long long>(s.stats.blocks), static_cast<unsigned long long>(s.stats.records),
                static_cast<unsigned long long>(s.prompts), static_cast<unsigned long long>(s.delayeds),
                static_cast<unsigned long long>(s.tags));
    std::printf("  time %.6f s to %.6f s (%.6f s, %.0f prompts/s), time resets %llu\n",
                static_cast<double>(s.first_ps) * 1e-12, static_cast<double>(s.last_ps) * 1e-12, span_s,
                span_s > 0 ? static_cast<double>(s.prompts) / span_s : 0.0,
                static_cast<unsigned long long>(s.time_resets));
    std::printf("  lost: %llu blocks, %llu records; %llu bytes skipped\n",
                static_cast<unsigned long long>(s.stats.blocks_lost),
                static_cast<unsigned long long>(s.stats.records_lost),
                static_cast<unsigned long long>(s.stats.bytes_skipped));
    std::printf("  ends: %s\n", s.stats.end_of_run    ? "end of run"
                                : s.stats.end_of_file ? "end of file, the run continues in the next file"
                                                      : "no closing block (the writer did not finish this file)");
    print_issues(s.issues);
    if (!s.issues.empty() || !s.stats.end_of_file) {
      status = 1;
    }
  }
  return status;
}

// Every file intact and closed; the last one ends the run, the others continue it.
int verify(const std::vector<std::string>& files) {
  int bad = 0;
  for (std::size_t k = 0; k < files.size(); ++k) {
    const auto bytes = read_file(files[k]);
    lm::Reader r{bytes};
    std::string problem;
    if (!r.header()) {
      problem = std::string{"file header "} + std::string{lm::to_string(r.header().error())};
    } else {
      const auto s = walk(r, [](const Coincidence&) {});
      const bool last = k + 1 == files.size();
      if (!s.issues.empty()) {
        problem = std::to_string(s.issues.size()) + " damaged or missing block(s), " +
                  std::to_string(s.stats.records_lost) + " records lost";
      } else if (!s.stats.end_of_file) {
        problem = "no closing block";
      } else if (last != s.stats.end_of_run) {
        problem = last ? "the run continues after the last file given" : "the run ends before the last file";
      }
    }
    std::printf("%s: %s\n", files[k].c_str(), problem.empty() ? "ok" : problem.c_str());
    bad += problem.empty() ? 0 : 1;
  }
  return bad == 0 ? 0 : 1;
}

bool write_raw(const std::string& path, std::span<const std::byte> data) {
  std::ofstream out{path, std::ios::binary};
  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-reinterpret-cast): ostream writes chars
  out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
  return static_cast<bool>(out.flush());
}

template <typename T>
std::vector<std::byte> little_endian(const std::vector<T>& v) {
  std::vector<std::byte> out(v.size() * sizeof(T));
  for (std::size_t i = 0; i < v.size(); ++i) {
    for (std::size_t b = 0; b < sizeof(T); ++b) {
      out[i * sizeof(T) + b] = static_cast<std::byte>((static_cast<std::uint64_t>(v[i]) >> (8 * b)) & 0xFFU);
    }
  }
  return out;
}

int sino(const std::vector<std::string>& files, const std::string& prefix, sino::SinogramConfig cfg) {
  // The delayed window's offset is in the metadata of the first file.
  {
    const auto bytes = read_file(files.front());
    const auto h = lm::parse_file_header(bytes);
    if (!h) {
      std::fprintf(stderr, "minidaq_listmode: %s: file header %s\n", files.front().c_str(),
                   std::string{lm::to_string(h.error())}.c_str());
      return 1;
    }
    const auto meta = nlohmann::json::parse(h->metadata, nullptr, /*allow_exceptions=*/false);
    if (meta.is_object() && meta.contains("records") && meta["records"].contains("delayed_window_ps")) {
      cfg.delayed_window_ps = meta["records"]["delayed_window_ps"].get<std::int64_t>();
    } else {
      std::fprintf(stderr, "minidaq_listmode: no records.delayed_window_ps in the metadata; using %lld ps\n",
                   static_cast<long long>(cfg.delayed_window_ps));
    }
  }
  if (auto v = sino::validate(cfg); !v) {
    std::fprintf(stderr, "minidaq_listmode: %s\n", v.error().c_str());
    return 2;
  }
  sino::Histogrammer h{cfg};
  int status = 0;
  for (const auto& f : files) {
    const auto bytes = read_file(f);
    lm::Reader r{bytes};
    const auto s = walk(r, [&](const Coincidence& c) { h.add(c); });
    if (!s.issues.empty()) {
      std::fprintf(stderr, "%s: %zu issue(s), %llu records lost; histogrammed what was intact\n", f.c_str(),
                   s.issues.size(), static_cast<unsigned long long>(s.stats.records_lost));
      status = 1;
    }
  }
  const auto& st = h.stats();
  const std::string pf = prefix + ".prompts.u32";
  const std::string df = prefix + ".delayeds.u32";
  const std::string mf = prefix + ".michelogram.u64";
  const auto name = [](const std::string& p) { return p.substr(p.find_last_of('/') + 1); };
  std::string comment = "from";
  for (const auto& f : files) {
    comment += " " + name(f);
  }
  const std::string hdr = sino::interfile_header(h, name(pf), name(df), comment);
  std::vector<std::uint32_t> plane;
  for (const auto v : h.collapsed()) {
    plane.push_back(static_cast<std::uint32_t>(v));
  }
  if (!write_raw(prefix + ".hdr", std::as_bytes(std::span{hdr})) || !write_raw(pf, little_endian(h.prompts())) ||
      !write_raw(df, little_endian(h.delayeds())) || !write_raw(mf, little_endian(h.michelogram())) ||
      !write_raw(prefix + ".prompts2d.u32", little_endian(plane))) {
    std::fprintf(stderr, "minidaq_listmode: cannot write %s.*\n", prefix.c_str());
    return 1;
  }
  std::printf("binned %llu prompts, %llu delayeds; outside the FOV %llu, above the ring difference %llu, "
              "outside the TOF range %llu, no angle %llu, invalid %llu\n",
              static_cast<unsigned long long>(st.prompts), static_cast<unsigned long long>(st.delayeds),
              static_cast<unsigned long long>(st.outside_fov), static_cast<unsigned long long>(st.ring_difference),
              static_cast<unsigned long long>(st.tof_outside), static_cast<unsigned long long>(st.no_angle),
              static_cast<unsigned long long>(st.invalid_crystal));
  std::printf("wrote %s.hdr: %u TOF x %u slices x %u views x %u radial bins (%zu bytes per sinogram)\n",
              prefix.c_str(), cfg.tof_bins, sino::num_ssrb_slices, sino::num_views, h.radial_bins(),
              h.prompts().size() * 4);
  return status;
}

int run(int argc, char** argv) {
  if (argc < 3) {
    std::fputs(usage, stderr);
    return 2;
  }
  const std::string_view cmd{argv[1]};
  std::vector<std::string> files;
  std::string out;
  sino::SinogramConfig cfg;
  bool ok = true;
  for (int i = 2; i < argc && ok; ++i) {
    const std::string_view a{argv[i]};
    const bool has_value = i + 1 < argc;
    const std::string_view v = has_value ? argv[i + 1] : "";
    if (cmd == "sino" && a == "--out" && has_value) {
      out = v;
    } else if (cmd == "sino" && a == "--fov" && has_value) {
      ok = parse_into(v, cfg.fov_radius_mm, 1.0, 149.0);
    } else if (cmd == "sino" && a == "--mrd" && has_value) {
      ok = parse_into(v, cfg.max_ring_difference, std::uint32_t{0}, std::uint32_t{47});
    } else if (cmd == "sino" && a == "--tof-bins" && has_value) {
      ok = parse_into(v, cfg.tof_bins, std::uint32_t{1}, std::uint32_t{255});
    } else if (cmd == "sino" && a == "--tof-bin-ps" && has_value) {
      ok = parse_into(v, cfg.tof_bin_ps, std::int64_t{1}, std::int64_t{100'000});
    } else if (a.starts_with("--")) {
      ok = false;
    } else {
      files.emplace_back(a);
      continue;
    }
    ++i;  // the option's value
  }
  if (!ok || files.empty() || (cmd == "sino" && out.empty())) {
    std::fputs(usage, stderr);
    return 2;
  }
  if (cmd == "info") {
    return info(files);
  }
  if (cmd == "verify") {
    return verify(files);
  }
  if (cmd == "sino") {
    return sino(files, out, cfg);
  }
  std::fputs(usage, stderr);
  return 2;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {
    std::fprintf(stderr, "minidaq_listmode: %s\n", e.what());
    return 2;
  }
}
