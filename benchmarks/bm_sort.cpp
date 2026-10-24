// SPDX-License-Identifier: MIT
// The sort stage's per-batch sort (Chapter 5). The same std::sort with the same
// ordering, called three ways:
//   FunctionPointer  std::sort(..., time_order): the comparator is a function
//                    pointer, which the compiler did not inline (Chapter 3's code)
//   Lambda           std::sort(..., [](a, b) { return time_order(a, b); })
//   Functor          std::sort(..., TimeOrder{}): a stateless function object
// Arguments: batch size, and input order (0: as decoded from the synthetic
// source, already nearly time-ordered; 1: shuffled).
#include <benchmark/benchmark.h>

#include <algorithm>
#include <random>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/synthetic_source.hpp"

namespace {

using minidaq::Single;

std::vector<Single> make_batches(std::size_t total, bool shuffled) {
  minidaq::sim::SyntheticSource gen{{}};
  std::vector<std::uint64_t> words(total);
  gen.generate(words);
  std::vector<Single> v(total);
  minidaq::packed::StreamDecoder dec{minidaq::ScannerGeometry::num_crystals};
  v.resize(dec.decode(words, v));
  if (shuffled) {
    std::shuffle(v.begin(), v.end(), std::mt19937_64{7});
  }
  return v;
}

template <typename Sort>
void run(benchmark::State& state, Sort sort) {
  const auto n = static_cast<std::size_t>(state.range(0));
  const std::size_t batches = 64;
  const auto pool = make_batches(n * batches, state.range(1) == 1);
  std::vector<Single> work(n);
  std::size_t b = 0;
  for (auto _ : state) {
    state.PauseTiming();  // copying the batch is not part of the sort
    std::copy_n(pool.begin() + static_cast<std::ptrdiff_t>(b * n), n, work.begin());
    b = (b + 1) % batches;
    state.ResumeTiming();
    sort(work);
    benchmark::DoNotOptimize(work.data());
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(n));
}

void BM_SortFunctionPointer(benchmark::State& state) {
  run(state, [](std::vector<Single>& v) { std::sort(v.begin(), v.end(), minidaq::time_order); });
}
void BM_SortLambda(benchmark::State& state) {
  run(state, [](std::vector<Single>& v) {
    std::sort(v.begin(), v.end(), [](const Single& a, const Single& b) { return minidaq::time_order(a, b); });
  });
}
void BM_SortFunctor(benchmark::State& state) {
  run(state, [](std::vector<Single>& v) { std::sort(v.begin(), v.end(), minidaq::TimeOrder{}); });
}

void args(benchmark::internal::Benchmark* b) {
  for (int order : {0, 1}) {
    for (int n : {512, 4096}) {
      b->Args({n, order});
    }
  }
}

}  // namespace

BENCHMARK(BM_SortFunctionPointer)->Apply(args);
BENCHMARK(BM_SortLambda)->Apply(args);
BENCHMARK(BM_SortFunctor)->Apply(args);
