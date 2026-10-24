// SPDX-License-Identifier: MIT
// End-to-end throughput of the five-stage pipeline (Chapter 3): pre-generated
// MDQ-P1 words go in, coincidences come out. The source copies from memory,
// so this measures the pipeline itself, not the generator.
// Arguments: batch size, batches per channel.
#include <benchmark/benchmark.h>

#include <algorithm>
#include <cstdint>
#include <vector>

#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/synthetic_source.hpp"

namespace {

constexpr std::uint64_t kWords = 1U << 23;  // about 8.4 M words

const std::vector<std::uint64_t>& words() {
  static const std::vector<std::uint64_t> w = [] {
    std::vector<std::uint64_t> v(kWords);
    minidaq::sim::SyntheticSource gen{{}};
    gen.generate(v);
    return v;
  }();
  return w;
}

void BM_Pipeline(benchmark::State& state) {
  const auto& w = words();
  std::uint64_t coincidences = 0;
  for (auto _ : state) {
    minidaq::PipelineConfig cfg;
    cfg.batch_size = static_cast<std::size_t>(state.range(0));
    cfg.batches_per_channel = static_cast<std::size_t>(state.range(1));
    cfg.total_words = kWords;
    std::size_t pos = 0;
    minidaq::AcquisitionPipeline p{cfg,
                                   [&](std::span<std::uint64_t> out) {
                                     const std::size_t k = std::min(out.size(), w.size() - pos);
                                     std::copy_n(w.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
                                     pos += k;
                                     return k;
                                   },
                                   [&](std::span<const minidaq::Coincidence> c) { coincidences += c.size(); }};
    p.start();
    p.wait();
  }
  benchmark::DoNotOptimize(coincidences);
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(kWords));
}

}  // namespace

BENCHMARK(BM_Pipeline)
    ->Args({64, 64})
    ->Args({512, 64})
    ->Args({4096, 64})
    ->Args({4096, 8})
    ->UseRealTime()->Unit(benchmark::kMillisecond);
