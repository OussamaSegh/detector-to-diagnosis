// SPDX-License-Identifier: MIT
// Heap merge (minidaq::StreamMerger) against slice-and-sort, for 4, 24 and 72
// boards, on singles split by block from a 20 MBq simulation. Slices of 10 us.
//   build/release/exercises/ch10/ch10_e5_slice_merge_solution_bench
#include <benchmark/benchmark.h>

#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/stream_merger.hpp"
#include "minidaq/sim/detector_simulator.hpp"
#include "slice_merge.hpp"

namespace {

using namespace minidaq;

std::vector<std::vector<Single>> split(std::size_t boards) {
  static const std::vector<Single> all = [] {
    sim::SimulatorConfig c;
    c.activity_bq = 20e6;
    c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
    c.phantom = {90.0, 180.0};
    c.seed = 3;
    sim::DetectorSimulator d{c};
    std::vector<Single> v;
    for (const auto& t : d.generate_until(Picoseconds{100'000'000'000})) {  // 0.1 s
      v.push_back(t.single);
    }
    return v;
  }();
  std::vector<std::vector<Single>> b(boards);
  for (const Single& s : all) {
    b[ScannerGeometry::block_of(s.crystal) % boards].push_back(s);
  }
  return b;
}

std::int64_t count(const std::vector<std::vector<Single>>& b) {
  std::int64_t n = 0;
  for (const auto& x : b) {
    n += static_cast<std::int64_t>(x.size());
  }
  return n;
}

void BM_Heap(benchmark::State& state) {
  const auto b = split(static_cast<std::size_t>(state.range(0)));
  std::vector<Single> out;
  for (auto _ : state) {
    StreamMerger m{{.boards = b.size(), .max_skew = Picoseconds{0}}};
    for (std::size_t i = 0; i < b.size(); ++i) {
      m.push(i, b[i]);
    }
    out.clear();
    m.flush(out);
    benchmark::DoNotOptimize(out.data());
  }
  state.SetItemsProcessed(state.iterations() * count(b));
}
BENCHMARK(BM_Heap)->Arg(4)->Arg(24)->Arg(72)->Unit(benchmark::kMillisecond);

void BM_Slices(benchmark::State& state) {
  const auto b = split(static_cast<std::size_t>(state.range(0)));
  for (auto _ : state) {
    auto out = ex105::merge_by_slices(b, Picoseconds{10'000'000});
    benchmark::DoNotOptimize(out.data());
  }
  state.SetItemsProcessed(state.iterations() * count(b));
}
BENCHMARK(BM_Slices)->Arg(4)->Arg(24)->Arg(72)->Unit(benchmark::kMillisecond);

}  // namespace
