// SPDX-License-Identifier: MIT
// End-to-end tests of the five-stage pipeline. The key property is
// conservation: every word that enters is either delivered or counted as
// dropped, at every stage. A second, stronger test compares the threaded
// output with a single-threaded reference computed from the same words.
#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <mutex>
#include <optional>
#include <thread>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/synthetic_source.hpp"

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

// Sequential version of decode + per-batch sort + pair. The source in the test
// delivers full batches, so batch boundaries fall every batch_size words.
std::vector<Coincidence> reference(const std::vector<std::uint64_t>& words, std::size_t batch_size,
                                   Picoseconds window) {
  std::vector<Single> singles(words.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  singles.resize(dec.decode(words, singles));
  for (std::size_t i = 0; i < singles.size(); i += batch_size) {
    const auto first = singles.begin() + static_cast<std::ptrdiff_t>(i);
    const auto last = singles.begin() + static_cast<std::ptrdiff_t>(std::min(i + batch_size, singles.size()));
    std::sort(first, last, time_order);
  }
  std::vector<Coincidence> out;
  std::optional<Single> carry;
  for (const Single& x : singles) {
    if (carry && x.time - carry->time <= window) {
      out.push_back(Coincidence{*carry, x, CoincidenceKind::prompt});
      carry.reset();
    } else {
      carry = x;
    }
  }
  return out;
}

void expect_conservation(const std::array<StageSnapshot, num_stages>& st) {
  const auto& [src, dec, srt, par, wri] = st;
  EXPECT_EQ(src.items_in, src.items_out + src.items_dropped) << "source";
  EXPECT_EQ(dec.items_in, src.items_out) << "decode received what source sent";
  EXPECT_EQ(dec.items_in, dec.items_out + dec.items_dropped + dec.items_filtered) << "decode";
  EXPECT_EQ(srt.items_in, dec.items_out) << "sort";
  EXPECT_EQ(srt.items_out, srt.items_in);
  EXPECT_EQ(par.items_in, srt.items_out) << "pair";
  EXPECT_EQ(par.items_in, 2 * par.items_out + par.items_filtered) << "pair: two singles per coincidence";
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

  const auto want = reference(words, small_config(n).batch_size, PipelineConfig{}.coincidence_window);
  ASSERT_EQ(got.size(), want.size());
  for (std::size_t i = 0; i < want.size(); ++i) {
    ASSERT_EQ(got[i].first.time, want[i].first.time) << i;
    ASSERT_EQ(got[i], want[i]) << i;
  }
  const auto st = p.stats();
  expect_conservation(st);
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
  AcquisitionPipeline p{cfg, [&](std::span<std::uint64_t> out) { return gen.generate(out); },
                        [](std::span<const Coincidence>) { std::this_thread::sleep_for(200us); }};  // slow disk
  p.start();
  p.wait();
  const auto st = p.stats();
  expect_conservation(st);
  EXPECT_EQ(st[0].items_in, n) << "the source read everything the hardware sent";
  EXPECT_GT(st[0].items_dropped, 0U) << "a slow sink with the drop policy must drop";
  EXPECT_EQ(st[0].items_out + st[0].items_dropped, n);
}

TEST(Pipeline, StopRequestDrainsInFlightData) {
  // REQ: SRS-PIPE-012
  sim::SyntheticSource gen{{}};
  std::uint64_t delivered = 0;
  AcquisitionPipeline p{small_config(0), [&](std::span<std::uint64_t> out) { return gen.generate(out); },
                        [&](std::span<const Coincidence> c) { delivered += c.size(); }};
  p.start();
  std::this_thread::sleep_for(50ms);
  p.request_stop();
  p.wait();
  const auto st = p.stats();
  expect_conservation(st);
  EXPECT_GT(st[0].items_out, 0U);
  EXPECT_EQ(delivered, st[4].items_in);
}

TEST(Pipeline, SourceWithNoDataDoesNotHang) {
  int calls = 0;
  AcquisitionPipeline p{small_config(0),
                        [&](std::span<std::uint64_t>) -> std::size_t {
                          ++calls;
                          return 0;
                        },
                        nullptr};
  p.start();
  std::this_thread::sleep_for(20ms);
  p.request_stop();
  p.wait();
  EXPECT_GT(calls, 0);
  EXPECT_EQ(p.stats()[0].items_out, 0U);
}

TEST(Pipeline, DestructorStopsARunningPipeline) {
  sim::SyntheticSource gen{{}};
  {
    AcquisitionPipeline p{small_config(0), [&](std::span<std::uint64_t> out) { return gen.generate(out); }, nullptr};
    p.start();
    std::this_thread::sleep_for(10ms);
  }  // must not hang or crash
  EXPECT_GT(gen.generated(), 0U);
}
