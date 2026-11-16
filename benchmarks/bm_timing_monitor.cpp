// SPDX-License-Identifier: MIT
// The cost of the time base monitor (Chapter 38): what record() adds to the pair stage for every
// coincidence, and what one evaluation of an interval costs, the fit of 72 block offsets to the
// shifts of every pair of blocks.
#include <benchmark/benchmark.h>

#include <cmath>
#include <cstdint>
#include <memory>
#include <random>
#include <span>
#include <vector>

#include "minidaq/processing/timing_monitor.hpp"

namespace {

using minidaq::Coincidence;
using minidaq::CoincidenceKind;
using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::Picoseconds;
using minidaq::ScannerGeometry;
using minidaq::Single;

// Coincidences of random crystals, 1 us apart, a tenth of them delayed: one interval of 1 s per
// million, so a run of the benchmark also closes intervals now and then, as a real run does.
std::vector<Coincidence> coincidences(std::size_t n) {
  std::mt19937_64 rng{38};
  std::uniform_int_distribution<std::uint32_t> crystal(0, ScannerGeometry::num_crystals - 1);
  std::normal_distribution<double> d(0.0, 400.0);
  std::vector<Coincidence> out;
  out.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    const auto t = static_cast<std::int64_t>(i) * 1'000'000;
    const bool delayed = i % 10 == 0;
    const auto dt = static_cast<std::int64_t>(std::abs(d(rng))) + (delayed ? 100'000 : 0);
    out.push_back(Coincidence{Single{Picoseconds{t}, CrystalId{crystal(rng)}, KeV{511.0F}},
                              Single{Picoseconds{t + dt}, CrystalId{crystal(rng)}, KeV{511.0F}},
                              delayed ? CoincidenceKind::delayed : CoincidenceKind::prompt});
  }
  return out;
}

// record() per coincidence, in batches of 4,096 as the pair stage hands them over.
void BM_TimingMonitorRecord(benchmark::State& state) {
  static const std::vector<Coincidence> c = coincidences(1U << 21);
  minidaq::TimingMonitorConfig cfg;
  cfg.delay = Picoseconds{100'000};
  auto monitor = std::make_unique<minidaq::TimingMonitor>(cfg);
  std::size_t at = 0;
  constexpr std::size_t batch = 4'096;
  for (auto _ : state) {
    if (at + batch > c.size()) {
      state.PauseTiming();
      monitor = std::make_unique<minidaq::TimingMonitor>(cfg);  // times start again
      at = 0;
      state.ResumeTiming();
    }
    monitor->record(std::span{c}.subspan(at, batch));
    at += batch;
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(batch));
}
BENCHMARK(BM_TimingMonitorRecord);

// One fit of the offsets of 72 blocks to the shifts of all 2,556 pairs of blocks.
void BM_TimingMonitorSolve(benchmark::State& state) {
  std::mt19937_64 rng{38};
  std::normal_distribution<double> noise(0.0, 20.0);
  std::vector<minidaq::PairShift> pairs;
  for (std::uint32_t a = 0; a < ScannerGeometry::num_blocks; ++a) {
    for (std::uint32_t b = a + 1; b < ScannerGeometry::num_blocks; ++b) {
      pairs.push_back({a, b, noise(rng), 400.0});
    }
  }
  for (auto _ : state) {
    benchmark::DoNotOptimize(minidaq::solve_block_offsets(ScannerGeometry::num_blocks, pairs));
  }
}
BENCHMARK(BM_TimingMonitorSolve)->Unit(benchmark::kMicrosecond);

}  // namespace
