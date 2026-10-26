// SPDX-License-Identifier: MIT
// Cost of the flight recorder (Chapter 21): recording one event, with and without a reader
// taking snapshots at the same time, and taking one full snapshot.
#include <benchmark/benchmark.h>

#include <atomic>
#include <cstdint>
#include <thread>
#include <vector>

#include "minidaq/core/flight_recorder.hpp"

namespace {

minidaq::FlightRecorder recorder;  // static storage: the recorder must outlive its writers

void BM_TraceRecord(benchmark::State& state) {
  std::uint64_t i = 0;
  for (auto _ : state) {
    recorder.record(minidaq::TraceCode::note, ++i, 0);
  }
  state.SetItemsProcessed(state.iterations());
}

// One writer, and a reader that copies the whole recorder over and over.
void BM_TraceRecordWhileReading(benchmark::State& state) {
  std::atomic<bool> stop{false};
  std::thread reader{[&] {
    std::vector<minidaq::TraceEvent> out(minidaq::FlightRecorder::kCapacity);
    while (!stop.load(std::memory_order_relaxed)) {
      benchmark::DoNotOptimize(recorder.snapshot_into(out));
    }
  }};
  std::uint64_t i = 0;
  for (auto _ : state) {
    recorder.record(minidaq::TraceCode::note, ++i, 0);
  }
  stop.store(true);
  reader.join();
  state.SetItemsProcessed(state.iterations());
}

void BM_TraceSnapshot(benchmark::State& state) {
  std::thread{[] {
    for (std::size_t i = 0; i < minidaq::FlightRecorder::kRingEvents; ++i) {
      recorder.record(minidaq::TraceCode::note, i, 0);
    }
  }}.join();
  std::vector<minidaq::TraceEvent> out(static_cast<std::size_t>(state.range(0)));
  for (auto _ : state) {
    benchmark::DoNotOptimize(recorder.snapshot_into(out));
  }
}

}  // namespace

BENCHMARK(BM_TraceRecord)->Threads(1)->Threads(4);
BENCHMARK(BM_TraceRecordWhileReading);
BENCHMARK(BM_TraceSnapshot)->Arg(64)->Arg(1024)->Unit(benchmark::kMicrosecond);
