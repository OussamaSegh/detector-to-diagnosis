// SPDX-License-Identifier: MIT
// Coincidence sorter and stream merger throughput (Chapter 10).
//
// Input: singles from the detector simulator at 20 MBq (a 90 mm water
// phantom), so window occupancy, multiples and energy rejection are those of a
// realistic stream rather than of uniform random data.
//   BM_Sorter/<policy>/<delayed>/<fov>  policy 0..3 as in MultiplesPolicy;
//                                       delayed and fov 0 (off) or 1 (on)
//   BM_SorterPerSingle                  per-single windows, kill_all, delayed on
//   BM_Merger/<boards>                  k-way merge of the same singles split by block
// Singles are pushed in batches of 4096, as the pipeline's pair stage does.
// items_per_second counts every single offered, including those the energy
// gate rejects (in_window is the fraction that passes).
#include <benchmark/benchmark.h>

#include <algorithm>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/stream_merger.hpp"
#include "minidaq/sim/detector_simulator.hpp"

namespace {

using namespace minidaq;

const std::vector<Single>& stream() {
  static const std::vector<Single> singles = [] {
    sim::SimulatorConfig c;
    c.activity_bq = 20e6;
    c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
    c.phantom = {90.0, 180.0};
    c.seed = 3;
    sim::DetectorSimulator d{c};
    std::vector<Single> v;
    for (const auto& t : d.generate_until(Picoseconds{200'000'000'000})) {  // 0.2 s
      v.push_back(t.single);
    }
    return v;
  }();
  return singles;
}

void sort_all(benchmark::State& state, const SorterConfig& cfg) {
  const auto& in = stream();
  constexpr std::size_t batch = 4096;
  std::vector<Coincidence> out;
  out.reserve(2 * batch);
  std::uint64_t found = 0;
  for (auto _ : state) {
    CoincidenceSorter s{cfg};
    for (std::size_t i = 0; i < in.size(); i += batch) {
      s.push(std::span{in}.subspan(i, std::min(batch, in.size() - i)), out);
      found += out.size();
      out.clear();
    }
    s.flush(out);
    found += out.size();
    out.clear();
    benchmark::DoNotOptimize(found);
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(in.size()));
  std::size_t in_window = 0;
  for (const Single& x : in) {
    const auto e = static_cast<double>(x.energy.count());
    in_window += e >= cfg.energy_low_kev && e <= cfg.energy_high_kev ? 1 : 0;
  }
  state.counters["in_window"] = static_cast<double>(in_window) / static_cast<double>(in.size());
  state.counters["coinc_per_single"] =
      static_cast<double>(found) / static_cast<double>(state.iterations()) / static_cast<double>(in.size());
}

void BM_Sorter(benchmark::State& state) {
  SorterConfig c;
  c.multiples = static_cast<MultiplesPolicy>(state.range(0));
  c.delay = state.range(1) != 0 ? Picoseconds{100'000} : Picoseconds{0};
  c.fov_radius_mm = state.range(2) != 0 ? 120.0 : 0.0;
  sort_all(state, c);
}
BENCHMARK(BM_Sorter)
    ->ArgsProduct({{0, 1, 2, 3}, {1}, {0}})
    ->Args({0, 0, 0})
    ->Args({0, 1, 1})
    ->Unit(benchmark::kMillisecond);

void BM_SorterPerSingle(benchmark::State& state) {
  SorterConfig c;
  c.mode = WindowMode::per_single;
  sort_all(state, c);
}
BENCHMARK(BM_SorterPerSingle)->Unit(benchmark::kMillisecond);

void BM_Merger(benchmark::State& state) {
  const auto& in = stream();
  const auto boards = static_cast<std::size_t>(state.range(0));
  std::vector<std::vector<Single>> per_board(boards);
  for (const Single& s : in) {
    per_board[ScannerGeometry::block_of(s.crystal) % boards].push_back(s);
  }
  // Each board delivers 64 singles at a time, round robin, like packets.
  constexpr std::size_t chunk = 64;
  std::vector<Single> out;
  out.reserve(in.size());
  for (auto _ : state) {
    StreamMerger m{{.boards = boards, .max_skew = Picoseconds{0}}};
    std::vector<std::size_t> pos(boards, 0);
    bool more = true;
    while (more) {
      more = false;
      for (std::size_t b = 0; b < boards; ++b) {
        const std::size_t n = std::min(chunk, per_board[b].size() - pos[b]);
        m.push(b, std::span{per_board[b]}.subspan(pos[b], n));
        pos[b] += n;
        more = more || pos[b] < per_board[b].size();
      }
      m.drain(out);
    }
    m.flush(out);
    benchmark::DoNotOptimize(out.data());
    out.clear();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(in.size()));
}
BENCHMARK(BM_Merger)->Arg(4)->Arg(24)->Arg(72)->Unit(benchmark::kMillisecond);

}  // namespace
