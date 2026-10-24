// SPDX-License-Identifier: MIT
// minidaq_latency: run the acquisition pipeline at a fixed input rate and
// report per-stage service time and end-to-end latency percentiles (Chapter 4).
// With --words, replay a recorded stream (minidaq_sim --words) instead of
// synthetic words, at --speed times its own rate or at --rate, and report how
// busy each stage was, to find the first bottleneck (Chapter 11).
//
//   minidaq_latency --rate 10e6 --seconds 20 --profile minidaq/profiles/rt-pin.conf
//   minidaq_latency --words nema-100MBq.bin --speed 1 --seconds 5
#include <array>
#include <cstdio>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/paced_source.hpp"
#include "minidaq/sim/replay_source.hpp"

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
  std::string words_path;
  double speed = 0.0;  // 0: use --rate
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
    } else if (a == "--words" && !v.empty()) {
      words_path = v;
    } else if (a == "--speed") {
      ok = minidaq::parse_into(v, speed, 1e-3, 1e3);
    } else if (a == "--profile" && !v.empty()) {
      profile_path = v;
    } else {
      ok = false;
    }
    if (!ok) {
      std::fprintf(stderr,
                   "usage: %s [--rate WORDS_PER_S] [--seconds S] [--batch N] [--profile FILE]\n"
                   "          [--words FILE [--speed X]]\n",
                   argv[0]);
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
  std::vector<std::uint64_t> recorded;
  if (!words_path.empty()) {
    std::ifstream f{words_path, std::ios::binary};
    unsigned char bytes[8];  // NOLINT(cppcoreguidelines-avoid-c-arrays,modernize-avoid-c-arrays): read buffer
    while (f.read(reinterpret_cast<char*>(bytes), sizeof bytes)) {  // NOLINT(cppcoreguidelines-pro-type-reinterpret-cast): byte buffer
      std::uint64_t w = 0;
      for (int i = 7; i >= 0; --i) {
        w = (w << 8U) | bytes[i];  // little-endian, as minidaq_sim writes it
      }
      recorded.push_back(w);
    }
    if (recorded.size() < 2) {
      std::fprintf(stderr, "%s: cannot read at least two words\n", words_path.c_str());
      return 1;
    }
  }
  minidaq::sim::PacedSource paced{{}, rate, batch};
  std::unique_ptr<minidaq::sim::ReplaySource> replay;
  if (!recorded.empty()) {
    replay = std::make_unique<minidaq::sim::ReplaySource>(std::move(recorded), speed > 0.0 ? 0.0 : rate, batch);
    if (speed > 0.0) {
      replay->set_rate(speed * replay->real_time_rate());
    }
    rate = replay->rate();
  }
  // Measure from when each batch's first word was due, not when it was read.
  if (replay) {
    cfg.due_time_ns = [&replay](std::uint64_t index) { return replay->due_ns(index); };
  } else {
    cfg.due_time_ns = [&paced](std::uint64_t index) { return paced.due_ns(index); };
  }
  minidaq::AcquisitionPipeline::WordSource source;
  if (replay) {
    source = std::ref(*replay);
  } else {
    source = std::ref(paced);
  }
  minidaq::AcquisitionPipeline pipe{cfg, std::move(source), nullptr};
  const std::int64_t t_start = minidaq::monotonic_ns();
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
  const std::int64_t t_end = minidaq::monotonic_ns();
  const std::uint64_t behind = replay ? replay->behind(t_end) : paced.behind(t_end);

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
  // How busy each stage was: the sum of its batch service times over the
  // run's wall time. The first stage to approach 100% is the bottleneck.
  const double wall_ns = static_cast<double>(t_end - t_start);
  std::printf("%-12s %12s %7s %12s %12s %12s\n", "stage", "items in", "busy %", "out stalls", "in idle", "dropped");
  for (std::size_t i = 0; i < minidaq::num_stages; ++i) {
    const auto l = pipe.stage_latency(static_cast<minidaq::StageId>(i)).summary();
    std::printf("%-12s %12llu %7.1f %12llu %12llu %12llu\n", names[i], static_cast<unsigned long long>(st[i].items_in),
                100.0 * static_cast<double>(l.count) * l.mean / wall_ns,
                static_cast<unsigned long long>(st[i].output_stalls), static_cast<unsigned long long>(st[i].input_idle),
                static_cast<unsigned long long>(st[i].items_dropped));
  }
  const auto so = pipe.sorter_stats();
  std::printf("sorter: %llu singles, %llu energy rejected, %llu out of order, %llu prompts, %llu delayed\n",
              static_cast<unsigned long long>(so.singles_in), static_cast<unsigned long long>(so.energy_rejected),
              static_cast<unsigned long long>(so.out_of_order), static_cast<unsigned long long>(so.prompts),
              static_cast<unsigned long long>(so.delayed));
  return 0;
}
