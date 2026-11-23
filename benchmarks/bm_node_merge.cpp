// SPDX-License-Identifier: MIT
// The cost of several readout nodes (CR-0037): the synthetic source read out
// by 1, 2, 4 and 8 nodes and merged, against the source alone. One node
// bypasses the merge, as the pipeline does. The difference per single is the
// merge's cost: dividing among the nodes, correcting the clocks and the k-way
// merge of Chapter 10. BM_PipelineWithNodes is the whole pipeline of
// bm_pipeline with the merge in its source stage: the nodes' streams are
// generated beforehand, so that it measures the merge and the pipeline, not
// the generator.
//   build/release/benchmarks/bm_node_merge --benchmark_repetitions=5
#include <benchmark/benchmark.h>

#include <algorithm>
#include <cstdint>
#include <vector>

#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/processing/node_merge.hpp"

#include "minidaq/sim/node_source.hpp"
#include "minidaq/sim/readout_nodes.hpp"
#include "minidaq/sim/synthetic_source.hpp"

using namespace minidaq;

namespace {

constexpr std::size_t batch = 4096;

void BM_SourceAlone(benchmark::State& state) {
  sim::SyntheticSource src{{.rate_hz = 10e6, .seed = 1}};
  std::vector<std::uint64_t> words(batch);
  for (auto _ : state) {
    src.generate(words);
    benchmark::DoNotOptimize(words.data());
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(batch));
}
BENCHMARK(BM_SourceAlone);

void BM_NodesMerged(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  std::vector<Picoseconds> offsets(n);
  for (std::size_t k = 0; k < n; ++k) {
    offsets[k] = Picoseconds{static_cast<std::int64_t>(k) * 200'000 - 500'000};
  }
  sim::MultiNodeSource src{{.rate_hz = 10e6, .seed = 1}, sim::NodeLayout::contiguous(n, offsets)};
  std::vector<std::uint64_t> words(batch);
  for (auto _ : state) {
    src.generate(words);
    benchmark::DoNotOptimize(words.data());
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(batch));
}
BENCHMARK(BM_NodesMerged)->Arg(2)->Arg(4)->Arg(8);

constexpr std::size_t kSingles = std::size_t{1} << 22;  // about 4.2 M singles

void BM_PipelineWithNodes(benchmark::State& state) {
  const auto n = static_cast<std::size_t>(state.range(0));
  std::vector<Single> all(kSingles);
  sim::SyntheticSource gen{{.rate_hz = 10e6, .seed = 1}};
  gen.generate(std::span<Single>{all});
  std::vector<Picoseconds> offsets(n);
  for (std::size_t k = 0; k < n; ++k) {
    offsets[k] = Picoseconds{static_cast<std::int64_t>(k) * 200'000 - 300'000};
  }
  const auto layout = sim::NodeLayout::contiguous(n, n == 1 ? std::vector<Picoseconds>{} : offsets);
  std::vector<std::vector<Single>> per_node;
  sim::NodeSplitter{layout}.split(all, per_node);
  std::vector<std::uint64_t> plain(kSingles);
  std::transform(all.begin(), all.end(), plain.begin(),
                 [](const Single& s) { return packed::encode(s); });
  std::uint64_t coincidences = 0;
  for (auto _ : state) {
    PipelineConfig cfg;
    cfg.total_words = kSingles;
    std::size_t pos = 0;  // one node: words delivered
    NodeMerge merge{layout.clock_offset};
    std::vector<std::size_t> at(n, 0);
    std::vector<Single> ready;
    std::size_t next = 0;
    AcquisitionPipeline::WordSource source;
    if (n == 1) {
      source = [&](std::span<std::uint64_t> out) {  // the path of 2.1: no merge
        const std::size_t k = std::min(out.size(), plain.size() - pos);
        std::copy_n(plain.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
        pos += k;
        return k;
      };
    } else {
      source = [&](std::span<std::uint64_t> out) {
        if (next == ready.size()) {
          ready.clear();
          next = 0;
          bool all_ended = true;
          for (std::size_t k = 0; k < n; ++k) {  // each node sends a chunk, then its time
            const auto& v = per_node[k];
            const std::size_t c = std::min<std::size_t>(512, v.size() - at[k]);
            merge.push(k, std::span{v}.subspan(at[k], c));
            at[k] += c;
            if (at[k] == v.size()) {
              merge.end(k);
            } else {
              merge.advance(k, v[at[k]].time);
              all_ended = false;
            }
          }
          if (all_ended) {
            merge.flush(ready);
          } else {
            merge.drain(ready);
          }
        }
        const std::size_t k = std::min(out.size(), ready.size() - next);
        for (std::size_t i = 0; i < k; ++i) {
          out[i] = packed::encode(ready[next + i]);
        }
        next += k;
        return k;
      };
    }
    AcquisitionPipeline p{cfg, source,
                          [&](std::span<const Coincidence> c) { coincidences += c.size(); }};
    p.start();
    p.wait();
  }
  benchmark::DoNotOptimize(coincidences);
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(kSingles));
}
BENCHMARK(BM_PipelineWithNodes)
    ->Arg(1)
    ->Arg(2)
    ->Arg(4)
    ->UseRealTime()
    ->Unit(benchmark::kMillisecond);

}  // namespace
