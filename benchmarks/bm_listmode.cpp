// SPDX-License-Identifier: MIT
// List-mode format throughput (Chapter 12): CRC-32, encoding, reading and
// histogramming, all in memory, so that the disk is not what is measured.
//
//   BM_Crc32Bytewise / BM_Crc32Slicing8   64 KiB, the size of a default block
//   BM_EncodeBlocks                       BlockWriter.append + finish, 4096-record blocks
//   BM_ReadBlocks                         Reader.next (both CRCs) + decode_record
//   BM_Histogram                          Histogrammer.add, no TOF
// The coincidences come from the detector simulator and the sorter (20 MBq,
// 90 mm water phantom, FOV cut at 120 mm), so crystals and times are those of
// a realistic stream.
#include <benchmark/benchmark.h>

#include <algorithm>
#include <random>
#include <vector>

#include "minidaq/core/crc32.hpp"
#include "minidaq/format/list_mode.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/sinogram.hpp"
#include "minidaq/sim/detector_simulator.hpp"

namespace {

using namespace minidaq;
namespace lm = minidaq::listmode;

const std::vector<Coincidence>& coincidences() {
  static const std::vector<Coincidence> out = [] {
    sim::SimulatorConfig c;
    c.activity_bq = 20e6;
    c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
    c.phantom = {90.0, 180.0};
    c.seed = 5;
    sim::DetectorSimulator d{c};
    std::vector<Single> singles;
    for (const auto& t : d.generate_until(Picoseconds{500'000'000'000})) {  // 0.5 s
      singles.push_back(t.single);
    }
    SorterConfig sc;
    sc.fov_radius_mm = 120.0;
    CoincidenceSorter s{sc};
    std::vector<Coincidence> v;
    s.push(singles, v);
    s.flush(v);
    return v;
  }();
  return out;
}

const std::vector<std::byte>& file() {
  static const std::vector<std::byte> f = [] {
    std::vector<std::byte> out = lm::encode_file_header("{}");
    std::vector<std::byte> buf(lm::block_bytes(4096));
    lm::BlockWriter w{buf, 4096};
    std::uint32_t seq = 0;
    auto emit = [&] {
      const auto n = w.finish(seq++, 0);
      out.insert(out.end(), buf.begin(), buf.begin() + static_cast<std::ptrdiff_t>(n));
      w.reset();
    };
    for (const auto& c : coincidences()) {
      if (w.append(c) != lm::BlockWriter::Append::ok) {
        emit();
        (void)w.append(c);
      }
    }
    emit();
    return out;
  }();
  return f;
}

void BM_Crc32Bytewise(benchmark::State& state) {
  std::vector<std::byte> data(64 * 1024);
  std::mt19937 rng{1};
  std::generate(data.begin(), data.end(), [&] { return static_cast<std::byte>(rng()); });
  for (auto _ : state) {
    benchmark::DoNotOptimize(crc32_bytewise(data));
  }
  state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(data.size()));
}
BENCHMARK(BM_Crc32Bytewise);

void BM_Crc32Slicing8(benchmark::State& state) {
  std::vector<std::byte> data(64 * 1024);
  std::mt19937 rng{1};
  std::generate(data.begin(), data.end(), [&] { return static_cast<std::byte>(rng()); });
  for (auto _ : state) {
    benchmark::DoNotOptimize(crc32(data));
  }
  state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(data.size()));
}
BENCHMARK(BM_Crc32Slicing8);

void BM_EncodeBlocks(benchmark::State& state) {
  const auto& in = coincidences();
  std::vector<std::byte> buf(lm::block_bytes(4096));
  std::uint64_t blocks = 0;
  for (auto _ : state) {
    lm::BlockWriter w{buf, 4096};
    for (const auto& c : in) {
      if (w.append(c) != lm::BlockWriter::Append::ok) {
        benchmark::DoNotOptimize(w.finish(0, 0));
        ++blocks;
        w.reset();
        (void)w.append(c);
      }
    }
    benchmark::DoNotOptimize(w.finish(0, 0));
    ++blocks;
    benchmark::ClobberMemory();
  }
  const auto n = state.iterations() * static_cast<std::int64_t>(in.size());
  state.SetItemsProcessed(n);
  state.SetBytesProcessed(n * static_cast<std::int64_t>(lm::record_bytes));
  state.counters["records_per_block"] = static_cast<double>(n) / static_cast<double>(blocks);
}
BENCHMARK(BM_EncodeBlocks)->Unit(benchmark::kMillisecond);

void BM_ReadBlocks(benchmark::State& state) {
  const auto& f = file();
  std::uint64_t records = 0;
  for (auto _ : state) {
    lm::Reader r{f};
    lm::BlockView b;
    std::int64_t sum = 0;
    while (r.next(b)) {
      for (std::size_t i = 0; i < b.record_count(); ++i) {
        sum += lm::decode_record(b, i).event.first.time.count();
      }
    }
    benchmark::DoNotOptimize(sum);
    records = r.stats().records;
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(records));
  state.SetBytesProcessed(state.iterations() * static_cast<std::int64_t>(f.size()));
}
BENCHMARK(BM_ReadBlocks)->Unit(benchmark::kMillisecond);

void BM_Histogram(benchmark::State& state) {
  const auto& in = coincidences();
  sino::Histogrammer h{sino::SinogramConfig{}};
  for (auto _ : state) {
    h.add(in);
    benchmark::ClobberMemory();
  }
  state.SetItemsProcessed(state.iterations() * static_cast<std::int64_t>(in.size()));
}
BENCHMARK(BM_Histogram)->Unit(benchmark::kMillisecond);

}  // namespace
