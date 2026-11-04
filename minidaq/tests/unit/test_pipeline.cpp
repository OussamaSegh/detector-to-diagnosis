// SPDX-License-Identifier: MIT
// End-to-end tests of the five-stage pipeline. The key property is
// conservation: every word that enters is either delivered or counted as
// dropped, at every stage. A second, stronger test compares the threaded
// output with a single-threaded reference computed from the same words.
#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <random>
#include <thread>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/synthetic_source.hpp"
#include "eventually.hpp"

using namespace minidaq;
using namespace std::chrono_literals;

namespace {

PipelineConfig small_config(std::uint64_t total) {
  PipelineConfig cfg;
  cfg.batch_size = 512;
  cfg.batches_per_channel = 8;
  cfg.total_words = total;
  return cfg;
}

// Sequential version of decode + per-batch sort + the coincidence sorter. The
// source in the test delivers full batches, so batch boundaries fall every
// batch_size words.
std::vector<Coincidence> reference(const std::vector<std::uint64_t>& words, std::size_t batch_size,
                                   const SorterConfig& sorter) {
  std::vector<Single> singles(words.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  singles.resize(dec.decode(words, singles));
  for (std::size_t i = 0; i < singles.size(); i += batch_size) {
    const auto first = singles.begin() + static_cast<std::ptrdiff_t>(i);
    const auto last = singles.begin() + static_cast<std::ptrdiff_t>(std::min(i + batch_size, singles.size()));
    std::sort(first, last, time_order);
  }
  std::vector<Coincidence> out;
  CoincidenceSorter s{sorter};
  s.push(singles, out);
  s.flush(out);
  return out;
}

void expect_conservation(const std::array<StageSnapshot, num_stages>& st, const SorterStats& so) {
  const auto& [src, dec, srt, par, wri] = st;
  EXPECT_EQ(src.items_in, src.items_out + src.items_dropped) << "source";
  EXPECT_EQ(dec.items_in, src.items_out) << "decode received what source sent";
  EXPECT_EQ(dec.items_in, dec.items_out + dec.items_dropped + dec.items_filtered) << "decode";
  EXPECT_EQ(srt.items_in, dec.items_out) << "sort";
  EXPECT_EQ(srt.items_out, srt.items_in);
  EXPECT_EQ(par.items_in, srt.items_out) << "pair";
  EXPECT_EQ(par.items_in, so.singles_in) << "pair: the sorter saw every single";
  EXPECT_EQ(par.items_filtered, so.energy_rejected + so.out_of_order);
  EXPECT_EQ(par.items_out, so.prompts + so.delayed);
  EXPECT_EQ(so.singles_in, so.energy_rejected + so.out_of_order + so.singles_alone + 2 * so.pair_windows +
                               so.singles_in_multiples)
      << "sorter: every single in exactly one window (fixed mode)";
  EXPECT_EQ(wri.items_in, par.items_out) << "write received every coincidence";
}

}  // namespace

TEST(Pipeline, MatchesSingleThreadedReference) {
  // REQ: SRS-PIPE-010
  constexpr std::uint64_t n = 200'000;
  std::vector<std::uint64_t> words(n);
  sim::SyntheticSource gen{{}};
  gen.generate(words);

  std::size_t pos = 0;
  std::vector<Coincidence> got;  // only touched by the writer thread until wait()
  AcquisitionPipeline p{small_config(n),
                        [&](std::span<std::uint64_t> out) {
                          const std::size_t k = std::min(out.size(), words.size() - pos);
                          std::copy_n(words.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
                          pos += k;
                          return k;
                        },
                        [&](std::span<const Coincidence> c) { got.insert(got.end(), c.begin(), c.end()); }};
  p.start();
  p.wait();
  ASSERT_TRUE(p.finished());

  const auto want = reference(words, small_config(n).batch_size, PipelineConfig{}.sorter);
  ASSERT_EQ(got.size(), want.size());
  for (std::size_t i = 0; i < want.size(); ++i) {
    ASSERT_EQ(got[i].first.time, want[i].first.time) << i;
    ASSERT_EQ(got[i], want[i]) << i;
  }
  const auto st = p.stats();
  expect_conservation(st, p.sorter_stats());
  EXPECT_EQ(st[0].items_out, n);
  EXPECT_EQ(st[0].items_dropped, 0U) << "block policy never drops";
  EXPECT_EQ(p.late_singles(), 0U);
  EXPECT_GT(want.size(), n / 8) << "the generator should produce pairs";
}

TEST(Pipeline, DropPolicyCountsEveryLostWord) {
  // REQ: SRS-PIPE-011
  constexpr std::uint64_t n = 100'000;
  PipelineConfig cfg = small_config(n);
  cfg.source_overflow = OverflowPolicy::drop;
  cfg.batches_per_channel = 2;
  sim::SyntheticSource gen{{}};
  // The sink stalls until the source has read everything (or 10 s have
  // passed), so the channels must fill and the source must drop. A sink that is
  // merely slow is not enough: on a fast machine a debug build's source can be
  // slower still, and nothing drops (seen on a GitHub runner).
  std::atomic<bool> source_done{false};
  AcquisitionPipeline p{cfg,
                        [&](std::span<std::uint64_t> out) {
                          const std::size_t got = gen.generate(out);
                          if (gen.generated() >= n) {
                            source_done.store(true, std::memory_order_release);
                          }
                          return got;
                        },
                        [&](std::span<const Coincidence>) {
                          // clock: deadline
                          const auto deadline = std::chrono::steady_clock::now() + 10s;
                          while (!source_done.load(std::memory_order_acquire) &&
                                 // clock: deadline
                                 std::chrono::steady_clock::now() < deadline) {
                            std::this_thread::sleep_for(100us);  // sleep: poll
                          }
                        }};
  p.start();
  p.wait();
  const auto st = p.stats();
  expect_conservation(st, p.sorter_stats());
  EXPECT_EQ(st[0].items_in, n) << "the source read everything the hardware sent";
  EXPECT_GT(st[0].items_dropped, 0U) << "a slow sink with the drop policy must drop";
  EXPECT_EQ(st[0].items_out + st[0].items_dropped, n);
}

TEST(Pipeline, StopRequestDrainsInFlightData) {
  // REQ: SRS-PIPE-012
  sim::SyntheticSource gen{{}};
  std::uint64_t delivered = 0;
  std::atomic<std::uint64_t> produced{0};  // relaxed: it only shows that work happened
  AcquisitionPipeline p{small_config(0),
                        [&](std::span<std::uint64_t> out) {
                          const std::size_t n = gen.generate(out);
                          produced.fetch_add(n, std::memory_order_relaxed);
                          return n;
                        },
                        [&](std::span<const Coincidence> c) { delivered += c.size(); }};
  p.start();
  // Stop while data is in flight: after the source has produced some, however long that takes.
  ASSERT_TRUE(test_support::eventually([&] { return produced.load(std::memory_order_relaxed) >= 100'000; }));
  p.request_stop();
  p.wait();
  const auto st = p.stats();
  expect_conservation(st, p.sorter_stats());
  EXPECT_GT(st[0].items_out, 0U);
  EXPECT_EQ(delivered, st[4].items_in);
}

TEST(Pipeline, SourceWithNoDataDoesNotHang) {
  std::atomic<int> calls{0};  // relaxed: it only shows that the source was polled
  AcquisitionPipeline p{small_config(0),
                        [&](std::span<std::uint64_t>) -> std::size_t {
                          calls.fetch_add(1, std::memory_order_relaxed);
                          return 0;
                        },
                        nullptr};
  p.start();
  ASSERT_TRUE(test_support::eventually([&] { return calls.load(std::memory_order_relaxed) > 1; })) << "the source is polled";
  p.request_stop();
  p.wait();
  EXPECT_GT(calls.load(), 0);
  EXPECT_EQ(p.stats()[0].items_out, 0U);
}

TEST(Pipeline, DestructorStopsARunningPipeline) {
  sim::SyntheticSource gen{{}};
  std::atomic<std::uint64_t> produced{0};  // relaxed: it only shows that work happened
  {
    AcquisitionPipeline p{small_config(0),
                          [&](std::span<std::uint64_t> out) {
                            const std::size_t n = gen.generate(out);
                            produced.fetch_add(n, std::memory_order_relaxed);
                            return n;
                          },
                          nullptr};
    p.start();
    ASSERT_TRUE(test_support::eventually([&] { return produced.load(std::memory_order_relaxed) > 0; }));
  }  // must not hang or crash
  EXPECT_GT(gen.generated(), 0U);
}

TEST(Pipeline, RecordsStageAndEndToEndLatency) {
  // REQ: SRS-RT-010
  sim::SyntheticSource gen{{}};
  constexpr std::uint64_t n = 100'000;
  AcquisitionPipeline p{small_config(n), [&](std::span<std::uint64_t> out) { return gen.generate(out); }, nullptr};
  p.start();
  p.wait();
  const auto st = p.stats();
  for (std::size_t i = 0; i < num_stages; ++i) {
    const auto& h = p.stage_latency(static_cast<StageId>(i));
    EXPECT_GT(h.count(), 0U) << st[i].name;
    EXPECT_GT(h.summary().max, 0) << st[i].name;
  }
  // One service-time sample per batch for source, decode, sort and write.
  EXPECT_EQ(p.stage_latency(StageId::decode).count(), st[1].batches);
  EXPECT_EQ(p.stage_latency(StageId::write).count(), st[4].batches);
  EXPECT_EQ(p.end_to_end_latency().count(), st[4].batches);
  const auto e2e = p.end_to_end_latency().summary();
  EXPECT_GE(e2e.min, p.stage_latency(StageId::write).summary().min) << "end to end includes the write";
}

TEST(Pipeline, MeasuresFromDueTimeWhenTheSourceKnowsIt) {
  // REQ: SRS-RT-012
  // A source that says its data was due one second ago: every end-to-end
  // sample must include that second (no coordinated omission).
  sim::SyntheticSource gen{{}};
  PipelineConfig cfg = small_config(20'000);
  const std::int64_t long_ago = monotonic_ns() - 1'000'000'000;
  std::uint64_t asked_max = 0;
  cfg.due_time_ns = [&](std::uint64_t index) {
    asked_max = std::max(asked_max, index);
    return long_ago;
  };
  AcquisitionPipeline p{cfg, [&](std::span<std::uint64_t> out) { return gen.generate(out); }, nullptr};
  p.start();
  p.wait();
  const auto e2e = p.end_to_end_latency().summary();
  ASSERT_GT(e2e.count, 0U);
  EXPECT_GE(e2e.min, 1'000'000'000);
  EXPECT_LT(asked_max, 20'000U) << "indices count words from 0";
}

TEST(Pipeline, AppliesRealTimeProfileBeforeStartReturns) {
  // REQ: SRS-RT-011
  PipelineConfig cfg = small_config(10'000);
  cfg.rt.stages[1].cpu = 0;  // pin decode to CPU 0
  cfg.rt.prefault_stack_bytes = 64 * 1024;
  sim::SyntheticSource gen{{}};
  AcquisitionPipeline p{cfg, [&](std::span<std::uint64_t> out) { return gen.generate(out); }, nullptr};
  p.start();
  const auto& rt = p.rt_status();  // complete as soon as start() returns
  for (const auto& s : rt) {
    EXPECT_TRUE(s.applied);
    EXPECT_TRUE(s.scheduled);
  }
  EXPECT_TRUE(rt[1].pinned);
  EXPECT_EQ(rt[1].running_cpu, 0);
  EXPECT_FALSE(rt[0].pinned);
  p.wait();
}

namespace {

// A table with every crystal's own gain and a time offset within +-2 ns.
std::shared_ptr<const CalibrationTable> skewed_table(std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::int32_t> offset{-2'000, 2'000};
  std::uniform_real_distribution<float> gain{0.9F, 1.1F};
  std::vector<CrystalCalibration> k(ScannerGeometry::num_crystals);
  for (auto& e : k) {
    e = CrystalCalibration{0.0F, packed::energy_lsb_kev * gain(rng), 0.0F, offset(rng)};
  }
  auto t = CalibrationTable::make(
      CalibrationInfo{"CAL-TEST", 1, "MDQ-TEST", "2026-11-03T00:00:00Z", "2027-11-03T00:00:00Z", 25.0, "test"},
      std::move(k));
  return std::make_shared<const CalibrationTable>(std::move(*t));
}

}  // namespace

TEST(Pipeline, ABatchWithoutValidWordsAndAnIdentityTableChangeNothing) {
  // REQ: SRS-PIPE-010
  // REQ: SRS-CAL-002
  // A first batch of words that all name a crystal the scanner does not have decodes to an empty
  // batch; the identity table is the same as no table. Either way the output is the reference's.
  constexpr std::uint64_t n = 100'000;
  const std::size_t batch = small_config(n).batch_size;
  std::vector<std::uint64_t> words(n);
  sim::SyntheticSource gen{{}};
  gen.generate(words);
  std::fill_n(words.begin(), batch, packed::crystal_mask << packed::crystal_shift);
  const auto want = reference(words, batch, PipelineConfig{}.sorter);
  ASSERT_GT(want.size(), n / 10);
  for (const bool identity : {false, true}) {
    PipelineConfig cfg = small_config(n);
    if (identity) {
      cfg.calibration = std::make_shared<const CalibrationTable>(CalibrationTable::identity());
    }
    std::size_t pos = 0;
    std::vector<Coincidence> got;
    AcquisitionPipeline p{cfg,
                          [&](std::span<std::uint64_t> out) {
                            const std::size_t k = std::min(out.size(), words.size() - pos);
                            std::copy_n(words.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
                            pos += k;
                            return k;
                          },
                          [&](std::span<const Coincidence> c) { got.insert(got.end(), c.begin(), c.end()); }};
    p.start();
    p.wait();
    ASSERT_TRUE(p.finished());
    EXPECT_EQ(got, want) << "identity " << identity;
    const auto st = p.stats();
    expect_conservation(st, p.sorter_stats());
    EXPECT_EQ(st[1].items_filtered, batch) << "identity " << identity;
    EXPECT_EQ(p.late_singles(), 0U);
  }
}

TEST(Pipeline, CalibratesEverySingleAndTheCorrectionMakesNoneLate) {
  // REQ: SRS-CAL-002
  // REQ: SRS-CAL-003
  constexpr std::uint64_t n = 200'000;
  std::vector<std::uint64_t> words(n);
  sim::SyntheticSource gen{{}};
  gen.generate(words);
  const auto table = skewed_table(7);
  ASSERT_GT(table->time_spread_ps(), 3'900);

  PipelineConfig cfg = small_config(n);
  cfg.calibration = table;
  std::size_t pos = 0;
  std::vector<Coincidence> got;
  AcquisitionPipeline p{cfg,
                        [&](std::span<std::uint64_t> out) {
                          const std::size_t k = std::min(out.size(), words.size() - pos);
                          std::copy_n(words.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
                          pos += k;
                          return k;
                        },
                        [&](std::span<const Coincidence> c) { got.insert(got.end(), c.begin(), c.end()); }};
  p.start();
  p.wait();
  ASSERT_TRUE(p.finished());

  // The reference: decode, calibrate, order the whole stream, pair.
  std::vector<Single> singles(words.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  singles.resize(dec.decode(words, singles));
  table->apply(singles);
  // Ordered batch by batch, as without the hold, the corrected stream has late singles:
  // this test would not see a missing hold.
  {
    auto per_batch = singles;
    Picoseconds last{std::numeric_limits<std::int64_t>::min()};
    std::uint64_t late = 0;
    for (std::size_t i = 0; i < per_batch.size(); i += cfg.batch_size) {
      const auto first = per_batch.begin() + static_cast<std::ptrdiff_t>(i);
      const auto end = per_batch.begin() + static_cast<std::ptrdiff_t>(std::min(i + cfg.batch_size, per_batch.size()));
      std::sort(first, end, time_order);
      late += static_cast<std::uint64_t>(std::count_if(first, end, [&](const Single& s) { return s.time < last; }));
      last = std::max(last, (end - 1)->time);
    }
    EXPECT_GT(late, 20U);  // 47 with this seed
  }
  std::sort(singles.begin(), singles.end(), time_order);
  std::vector<Coincidence> want;
  CoincidenceSorter s{cfg.sorter};
  s.push(singles, want);
  s.flush(want);

  EXPECT_EQ(p.late_singles(), 0U);
  ASSERT_EQ(got.size(), want.size());
  for (std::size_t i = 0; i < want.size(); ++i) {
    ASSERT_EQ(got[i], want[i]) << i;
  }
  expect_conservation(p.stats(), p.sorter_stats());
  EXPECT_EQ(p.sorter_stats().out_of_order, 0U);
}

TEST(Pipeline, MonitorsThePhotopeakOfTheCalibratedSingles) {
  // REQ: SRS-CAL-006
  constexpr std::uint64_t n = 100'000;
  std::vector<std::uint64_t> words(n);
  sim::SyntheticSource gen{{}};
  gen.generate(words);
  std::vector<Single> singles(words.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  singles.resize(dec.decode(words, singles));
  PhotopeakMonitor want;
  want.record(singles);

  std::size_t pos = 0;
  AcquisitionPipeline p{small_config(n),
                        [&](std::span<std::uint64_t> out) {
                          const std::size_t k = std::min(out.size(), words.size() - pos);
                          std::copy_n(words.begin() + static_cast<std::ptrdiff_t>(pos), k, out.begin());
                          pos += k;
                          return k;
                        },
                        [](std::span<const Coincidence>) {}};
  p.start();
  p.wait();
  const auto got = p.photopeak().snapshot();
  const auto ref = want.snapshot();
  std::uint64_t total = 0;
  for (std::size_t b = 0; b < got.size(); ++b) {
    EXPECT_EQ(got[b].singles, ref[b].singles) << b;
    EXPECT_NEAR(got[b].mean_kev, ref[b].mean_kev, 1e-6) << b;
    total += got[b].singles;
  }
  EXPECT_GT(total, n / 4) << "the synthetic source should give photopeak singles";
}
