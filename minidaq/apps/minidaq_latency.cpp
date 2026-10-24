// SPDX-License-Identifier: MIT
// minidaq_latency: run the acquisition pipeline at a fixed input rate and
// report per-stage service time and end-to-end latency percentiles (Chapter 4).
//
//   minidaq_latency --rate 10e6 --seconds 20 --profile minidaq/profiles/rt-pin.conf
#include <array>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/paced_source.hpp"

namespace {

void print_row(const char* name, const minidaq::LatencySummary& s) {
  std::printf("%-12s %9llu %9.1f %9.1f %9.1f %9.1f %10.1f\n", name, static_cast<unsigned long long>(s.count),
              static_cast<double>(s.p50) / 1e3, static_cast<double>(s.p99) / 1e3,
              static_cast<double>(s.p999) / 1e3, static_cast<double>(s.p9999) / 1e3,
              static_cast<double>(s.max) / 1e3);
}

}  // namespace

int main(int argc, char** argv) {
  double rate = 10e6;
  double seconds = 10.0;
  std::size_t batch = 4096;
  std::string profile_path;
  for (int i = 1; i < argc; i += 2) {  // every option takes a value
    const std::string_view a{argv[i]};
    const std::string_view v = i + 1 < argc ? argv[i + 1] : "";
    bool ok = true;
    if (a == "--rate") {
      ok = minidaq::parse_into(v, rate, 1.0, 1e9);
    } else if (a == "--seconds") {
      ok = minidaq::parse_into(v, seconds, 1e-3, 86400.0);
    } else if (a == "--batch") {
      ok = minidaq::parse_into(v, batch, std::size_t{1}, std::size_t{1} << 20);
    } else if (a == "--profile" && !v.empty()) {
      profile_path = v;
    } else {
      ok = false;
    }
    if (!ok) {
      std::fprintf(stderr, "usage: %s [--rate WORDS_PER_S] [--seconds S] [--batch N] [--profile FILE]\n", argv[0]);
      return 2;
    }
  }
  minidaq::PipelineConfig cfg;
  cfg.batch_size = batch;
  cfg.source_overflow = minidaq::OverflowPolicy::drop;  // measure, do not back-pressure the "hardware"
  if (!profile_path.empty()) {
    const std::ifstream f{profile_path};
    std::stringstream ss;
    ss << f.rdbuf();
    auto p = minidaq::rt::parse_profile(ss.str());
    if (!f || !p) {
      std::fprintf(stderr, "%s: %s (line %d)\n", profile_path.c_str(), p ? "cannot read" : p.error().message.c_str(),
                   p ? 0 : p.error().line);
      return 1;
    }
    cfg.rt = *p;
  }
  minidaq::sim::PacedSource src{{}, rate, batch};
  // Measure from when each batch's first word was due, not when it was read.
  cfg.due_time_ns = [&src](std::uint64_t index) { return src.due_ns(index); };
  minidaq::AcquisitionPipeline pipe{cfg, std::ref(src), nullptr};
  pipe.start();
  if (cfg.rt.lock_memory && !pipe.memory_locked()) {
    std::fprintf(stderr, "warning: mlockall failed\n");
  }
  for (const auto& s : pipe.rt_status()) {
    if (s.error) {
      std::fprintf(stderr, "warning: stage settings: %s\n", s.error.message().c_str());
    }
  }
  std::this_thread::sleep_for(std::chrono::duration<double>(seconds));
  pipe.request_stop();
  pipe.wait();
  // Read on this thread after the source thread has finished (wait() joined it).
  const std::uint64_t behind = src.behind(minidaq::monotonic_ns());

  const auto st = pipe.stats();
  std::printf("rate %.3g words/s, %.0f s, batch %zu, delivered %llu, dropped %llu, behind schedule %llu\n", rate,
              seconds, batch, static_cast<unsigned long long>(st[0].items_out),
              static_cast<unsigned long long>(st[0].items_dropped), static_cast<unsigned long long>(behind));
  std::printf("%-12s %9s %9s %9s %9s %9s %10s   (microseconds)\n", "stage", "batches", "p50", "p99", "p99.9",
              "p99.99", "max");
  constexpr std::array<const char*, minidaq::num_stages> names{"source", "decode", "sort", "pair", "write"};
  for (std::size_t i = 0; i < minidaq::num_stages; ++i) {
    print_row(names[i], pipe.stage_latency(static_cast<minidaq::StageId>(i)).summary());
  }
  print_row("end-to-end", pipe.end_to_end_latency().summary());
  return 0;
}
