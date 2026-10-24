// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <optional>
#include <vector>

#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/sim/synthetic_source.hpp"
#include "pipeline.hpp"

using namespace minidaq;
using namespace std::chrono_literals;

namespace {

std::vector<std::uint64_t> make_words(std::size_t n) {
  std::vector<std::uint64_t> w(n);
  sim::SyntheticSource gen{{}};
  gen.generate(w);
  return w;
}

std::vector<Coincidence> reference(std::span<const std::uint64_t> words, const ex::Config& cfg) {
  std::vector<Single> s(words.size());
  packed::StreamDecoder d{ScannerGeometry::num_crystals};
  s.resize(d.decode(words, s));
  for (std::size_t i = 0; i < s.size(); i += cfg.batch_size) {
    std::sort(s.begin() + static_cast<std::ptrdiff_t>(i),
              s.begin() + static_cast<std::ptrdiff_t>(std::min(i + cfg.batch_size, s.size())), time_order);
  }
  std::vector<Coincidence> out;
  std::optional<Single> carry;
  for (const Single& x : s) {
    if (carry && x.time - carry->time <= cfg.window) {
      out.push_back({*carry, x, CoincidenceKind::prompt});
      carry.reset();
    } else {
      carry = x;
    }
  }
  return out;
}

void expect_conservation(const ex::Result& r, std::size_t input) {
  const auto& [dec, srt, par, wri] = r.stages;
  EXPECT_EQ(dec.in, input);
  EXPECT_EQ(dec.in, dec.out + dec.dropped + dec.filtered);
  EXPECT_EQ(srt.in, srt.out);
  EXPECT_EQ(par.in, 2 * par.out + par.filtered) << "two singles per coincidence";
  EXPECT_EQ(wri.in, wri.out);
  for (const auto& s : r.stages) {
    EXPECT_GE(s.busy_seconds, 0.0) << s.name;
    EXPECT_LE(s.busy_seconds, r.wall_seconds) << s.name;
  }
  EXPECT_EQ(srt.in, dec.out);
  EXPECT_EQ(par.in, srt.out);
  EXPECT_EQ(wri.in, par.out);
  EXPECT_EQ(srt.dropped + par.dropped + wri.dropped, 0U) << "only the entry stage may drop";
  EXPECT_EQ(r.coincidences.size(), wri.out);
}

}  // namespace

TEST(FourStage, BlockingRunMatchesReference) {
  const auto words = make_words(300'000);
  ex::Config cfg;
  const auto r = ex::run_pipeline(words, cfg);
  expect_conservation(r, words.size());
  const auto want = reference(words, cfg);
  ASSERT_EQ(r.coincidences.size(), want.size());
  EXPECT_TRUE(std::equal(want.begin(), want.end(), r.coincidences.begin()));
  EXPECT_EQ(r.stages[0].dropped, 0U);
  for (const auto& s : r.stages) {
    EXPECT_GT(s.busy_seconds, 0.0) << s.name;
    EXPECT_GT(s.throughput(), 0.0) << s.name;
  }
}

TEST(FourStage, SmallBatchesAndOddSizes) {
  const auto words = make_words(10'007);
  ex::Config cfg;
  cfg.batch_size = 37;
  cfg.queue_batches = 3;
  const auto r = ex::run_pipeline(words, cfg);
  expect_conservation(r, words.size());
  EXPECT_EQ(r.coincidences.size(), reference(words, cfg).size());
}

TEST(FourStage, DropPolicyCountsLosses) {
  const auto words = make_words(200'000);
  ex::Config cfg;
  cfg.overflow = ex::Overflow::drop;
  cfg.queue_batches = 2;
  cfg.write_delay = 300us;
  std::uint64_t delivered_batches = 0;
  const auto r = ex::run_pipeline(words, cfg, [&](std::span<const Coincidence>) { ++delivered_batches; });
  expect_conservation(r, words.size());
  EXPECT_GT(r.stages[0].dropped, 0U) << "a slow writer with the drop policy must cause drops";
  EXPECT_EQ(r.stages[0].out + r.stages[0].dropped + r.stages[0].filtered, words.size());
  EXPECT_GT(delivered_batches, 0U);
}

TEST(FourStage, EmptyInput) {
  const auto r = ex::run_pipeline({}, ex::Config{});
  expect_conservation(r, 0);
  EXPECT_TRUE(r.coincidences.empty());
}
