// SPDX-License-Identifier: MIT
// writer_throughput: how fast the list-mode sink writes to a real disk
// (Chapter 12, Exercise 12.3), and a target for the kill -9 crash test.
//
// Feeds the sink in batches of 4096 coincidences, as the pipeline's writer
// thread does, as fast as it accepts them, and reports the rate it sustained
// once close() has made everything durable (or not, with --fsync none).
//
//   writer_throughput --dir /data/tmp --coincidences 20e6 --fsync close
//   writer_throughput --dir /data/tmp --fsync interval --every 64 --buffers 16
//   writer_throughput --dir /data/tmp --forever 1       until killed (crash test)
#include <chrono>
#include <cstdio>
#include <exception>
#include <random>
#include <string>
#include <string_view>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/listmode_sink.hpp"
#include "minidaq/core/parse_number.hpp"

namespace {

using namespace minidaq;
using Clock = std::chrono::steady_clock;

int run(int argc, char** argv) {
  control::ListModeSinkConfig cfg;
  cfg.prefix = "bench";
  cfg.metadata = {{"format", "MDQ-L1"}, {"records", {{"delayed_window_ps", 100'000}}}};
  double total = 20e6;
  bool forever = false;
  std::string fsync = "close";
  std::uint64_t max_file_mb = 1024;
  for (int i = 1; i < argc; i += 2) {
    const std::string_view a{argv[i]};
    const std::string_view v = i + 1 < argc ? argv[i + 1] : "";
    bool ok = true;
    if (a == "--dir" && !v.empty()) {
      cfg.directory = v;
    } else if (a == "--coincidences") {
      ok = parse_into(v, total, 1.0, 1e12);
    } else if (a == "--fsync") {
      ok = v == "none" || v == "close" || v == "interval";
      fsync = v;
    } else if (a == "--every") {
      ok = parse_into(v, cfg.fsync_every_blocks, std::uint32_t{1}, std::uint32_t{1} << 20);
    } else if (a == "--records") {
      ok = parse_into(v, cfg.records_per_block, std::size_t{1}, std::size_t{65536});
    } else if (a == "--buffers") {
      ok = parse_into(v, cfg.buffers, std::size_t{2}, std::size_t{65536});
    } else if (a == "--max-file-mb") {
      ok = parse_into(v, max_file_mb, std::uint64_t{1}, std::uint64_t{1} << 20);
    } else if (a == "--forever") {
      ok = v == "0" || v == "1";
      forever = v == "1";
    } else {
      ok = false;
    }
    if (!ok) {
      std::fputs("usage: writer_throughput --dir DIR [--coincidences N] [--fsync none|close|interval] [--every N]\n"
                 "                         [--records N] [--buffers N] [--max-file-mb N] [--forever 0|1]\n",
                 stderr);
      return 2;
    }
  }
  cfg.fsync = fsync == "none" ? control::FsyncPolicy::none
              : fsync == "interval" ? control::FsyncPolicy::interval
                                    : control::FsyncPolicy::close;
  cfg.max_file_bytes = max_file_mb << 20U;
  cfg.run_name = std::to_string(Clock::now().time_since_epoch().count());

  // A pool of one million coincidences with random crystals, replayed with
  // increasing times: generating them costs much less than writing them.
  std::mt19937_64 rng{7};
  std::uniform_int_distribution<std::uint32_t> crystal(0, 18431);
  std::uniform_int_distribution<int> energy(435 * 32, 585 * 32);
  std::vector<Coincidence> pool(1 << 20);
  for (auto& c : pool) {
    c.first = Single{Picoseconds{0}, CrystalId{crystal(rng)}, KeV{static_cast<float>(energy(rng)) / 32.0F}};
    c.second = Single{Picoseconds{1500}, CrystalId{crystal(rng)}, KeV{static_cast<float>(energy(rng)) / 32.0F}};
  }
  constexpr std::size_t batch = 4096;
  constexpr std::int64_t spacing_ps = 200'000;  // 5 M coincidences per second of data time
  std::vector<Coincidence> out(batch);

  auto sink = control::ListModeSink::open(cfg, control::make_posix_file_ops());
  if (!sink) {
    std::fprintf(stderr, "writer_throughput: %s\n", sink.error().c_str());
    return 1;
  }
  const auto t0 = Clock::now();
  std::uint64_t sent = 0;
  std::int64_t t = 0;
  std::size_t at = 0;
  while (forever || static_cast<double>(sent) < total) {
    for (auto& c : out) {
      c = pool[at];
      c.first.time = Picoseconds{t};
      c.second.time = Picoseconds{t + 1500};
      t += spacing_ps;
      at = (at + 1) % pool.size();
    }
    (*sink)->write(out);
    sent += batch;
    if (forever && sent % (batch * 1024) == 0) {
      std::printf("sent %llu\n", static_cast<unsigned long long>(sent));
      (void)std::fflush(stdout);
    }
    if (auto f = (*sink)->fault()) {
      std::fprintf(stderr, "writer_throughput: %s\n", f->c_str());
      return 1;
    }
  }
  const auto t_written = Clock::now();
  const auto err = (*sink)->close("");
  const auto t_closed = Clock::now();
  if (err) {
    std::fprintf(stderr, "writer_throughput: %s\n", err->c_str());
    return 1;
  }
  const auto s = (*sink)->stats();
  const double secs = std::chrono::duration<double>(t_closed - t0).count();
  const double close_s = std::chrono::duration<double>(t_closed - t_written).count();
  std::printf("writer fsync=%s every=%u records=%zu buffers=%zu file_mb=%llu: %llu coincidences, %.1f MB in %.3f s "
              "(close %.3f s): %.2f M/s, %.0f MB/s; files %llu, waits %llu (%.0f ms), fsyncs %llu, max fsync %.1f ms, "
              "max block write %.2f ms\n",
              fsync.c_str(), cfg.fsync_every_blocks, cfg.records_per_block, cfg.buffers,
              static_cast<unsigned long long>(max_file_mb), static_cast<unsigned long long>(s.coincidences),
              static_cast<double>(s.bytes) / 1e6, secs, close_s, static_cast<double>(s.coincidences) / secs / 1e6,
              static_cast<double>(s.bytes) / secs / 1e6, static_cast<unsigned long long>(s.files),
              static_cast<unsigned long long>(s.buffer_waits), static_cast<double>(s.buffer_wait_ns) / 1e6,
              static_cast<unsigned long long>(s.fsyncs), static_cast<double>(s.max_fsync_ns) / 1e6,
              static_cast<double>(s.max_write_ns) / 1e6);
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception& e) {
    std::fprintf(stderr, "writer_throughput: %s\n", e.what());
    return 2;
  }
}
