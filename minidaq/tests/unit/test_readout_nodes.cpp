// SPDX-License-Identifier: MIT
// Several readout nodes (CR-0037): the simulator divides the scanner's blocks
// among nodes with their own clocks, and the node merge gives back one stream
// whose coincidences are those of the same singles sorted as one stream (the
// single-node oracle).
#include <gtest/gtest.h>

#include <algorithm>
#include <cstdint>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#include "minidaq/config/acquisition_config.hpp"
#include "minidaq/control/adapters.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/pipeline/acquisition_pipeline.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/node_merge.hpp"
#include "minidaq/sim/node_source.hpp"
#include "minidaq/sim/paced_source.hpp"
#include "minidaq/sim/readout_nodes.hpp"
#include "minidaq/sim/synthetic_source.hpp"

using namespace minidaq;
using sim::NodeLayout;

namespace {

constexpr std::size_t blocks = ScannerGeometry::num_blocks;

Single at(std::int64_t t, std::uint32_t crystal) {
  return Single{Picoseconds{t}, CrystalId{crystal}, KeV{511.0F}};
}

std::vector<Single> singles(std::size_t n, std::uint64_t seed, double rate_hz = 20e6) {
  sim::SyntheticSource gen{{.rate_hz = rate_hz, .seed = seed}};
  std::vector<Single> v(n);
  gen.generate(std::span<Single>{v});
  return v;
}

// Every coincidence the sorter finds in `in`, prompts and delayed.
std::vector<Coincidence> coincidences(const std::vector<Single>& in) {
  CoincidenceSorter sorter{SorterConfig{}};
  std::vector<Coincidence> out;
  for (std::size_t i = 0; i < in.size(); i += 4096) {
    std::vector<Single> batch(
        in.begin() + static_cast<std::ptrdiff_t>(i),
        in.begin() + static_cast<std::ptrdiff_t>(std::min(in.size(), i + 4096)));
    std::sort(batch.begin(), batch.end(), TimeOrder{});  // as the pipeline's sort stage does
    sorter.push(batch, out);
  }
  sorter.flush(out);
  return out;
}

// A random layout: random node of each block, random offsets within the bound.
NodeLayout random_layout(std::mt19937_64& rng) {
  const std::size_t n = 1 + rng() % sim::max_readout_nodes;
  std::vector<std::uint32_t> node_of_block(blocks);
  for (auto& b : node_of_block) {
    b = static_cast<std::uint32_t>(rng() % n);
  }
  std::uniform_int_distribution<std::int64_t> offset{-sim::max_node_clock_offset.count(),
                                                     sim::max_node_clock_offset.count()};
  std::vector<Picoseconds> offsets(n);
  for (auto& o : offsets) {
    o = Picoseconds{offset(rng)};
  }
  return NodeLayout::of_blocks(std::move(node_of_block), std::move(offsets));
}

// The nodes deliver their streams in chunks of random sizes, in a random
// interleaving, each followed now and then by a time marker, as separate
// acquisition PCs would; the merge releases what it can after each delivery.
std::vector<Single> merged(const std::vector<Single>& all, const NodeLayout& layout,
                           std::mt19937_64& rng, MergerStats* stats = nullptr) {
  const sim::NodeSplitter split{layout};
  std::vector<std::vector<Single>> per_node;
  split.split(all, per_node);
  NodeMerge merge{layout.clock_offset};
  std::vector<std::size_t> pos(per_node.size(), 0);
  std::vector<Single> out;
  std::size_t open = per_node.size();
  std::vector<bool> ended(per_node.size(), false);
  while (open > 0) {
    const std::size_t n = rng() % per_node.size();
    if (ended[n]) {
      continue;
    }
    const std::size_t k = std::min<std::size_t>(per_node[n].size() - pos[n], rng() % 300);
    merge.push(n, std::span{per_node[n]}.subspan(pos[n], k));
    pos[n] += k;
    if (pos[n] == per_node[n].size()) {
      merge.end(n);
      ended[n] = true;
      --open;
    } else if (rng() % 4 == 0) {
      merge.advance(n,
                    per_node[n][pos[n]].time);  // its next single's time: nothing earlier follows
    }
    merge.drain(out);
  }
  merge.flush(out);
  if (stats != nullptr) {
    *stats = merge.stats();
  }
  return out;
}

}  // namespace

TEST(ReadoutNodes, ContiguousRangesCoverEveryBlockAndCheckTheirBounds) {
  // REQ: SRS-SIM-025
  for (std::size_t n = 1; n <= sim::max_readout_nodes; ++n) {
    const auto l = NodeLayout::contiguous(n);
    ASSERT_EQ(l.node_of_block.size(), blocks);
    EXPECT_TRUE(std::is_sorted(l.node_of_block.begin(), l.node_of_block.end())) << n;
    for (std::uint32_t k = 0; k < n; ++k) {
      EXPECT_NE(std::find(l.node_of_block.begin(), l.node_of_block.end(), k), l.node_of_block.end())
          << "node " << k << " of " << n << " reads no block";
    }
  }
  EXPECT_THROW((void)NodeLayout::contiguous(0), std::invalid_argument);
  EXPECT_THROW((void)NodeLayout::contiguous(9), std::invalid_argument);
  EXPECT_NO_THROW(
      (void)NodeLayout::contiguous(2, {Picoseconds{1'000'000}, Picoseconds{-1'000'000}}));
  EXPECT_THROW((void)NodeLayout::contiguous(2, {Picoseconds{1'000'001}, Picoseconds{0}}),
               std::invalid_argument);
  EXPECT_THROW((void)NodeLayout::contiguous(2, {Picoseconds{0}}), std::invalid_argument);
  std::vector<std::uint32_t> bad(blocks, 0);
  bad[5] = 2;
  EXPECT_THROW((void)NodeLayout::of_blocks(bad, {Picoseconds{0}, Picoseconds{0}}),
               std::invalid_argument);
}

TEST(ReadoutNodes, EachNodeGetsItsBlocksInTimeOrderInItsOwnClock) {
  // REQ: SRS-SIM-025
  const auto all = singles(50'000, 3);
  const auto layout = NodeLayout::contiguous(
      4, {Picoseconds{700}, Picoseconds{-1'000'000}, Picoseconds{0}, Picoseconds{999'999}});
  const sim::NodeSplitter split{layout};
  std::vector<std::vector<Single>> per_node;
  split.split(all, per_node);
  ASSERT_EQ(per_node.size(), 4U);
  std::size_t total = 0;
  for (std::size_t n = 0; n < per_node.size(); ++n) {
    total += per_node[n].size();
    EXPECT_TRUE(std::is_sorted(per_node[n].begin(), per_node[n].end(),
                               [](const Single& a, const Single& b) { return a.time < b.time; }));
    for (const Single& s : per_node[n]) {
      ASSERT_EQ(layout.node_of(s.crystal), n);
    }
  }
  EXPECT_EQ(total, all.size());
  // Node 1 reads the first single's block only if the layout says so; its time is shifted by the
  // offset.
  const std::size_t first = layout.node_of(all.front().crystal);
  EXPECT_EQ(per_node[first].front().time, all.front().time + layout.clock_offset[first]);
}

TEST(ReadoutNodes, OneNodeIsTheStreamWithoutNodes) {
  // REQ: SRS-SIM-025
  const auto all = singles(20'000, 9);
  std::vector<std::vector<Single>> per_node;
  sim::NodeSplitter{NodeLayout::contiguous(1)}.split(all, per_node);
  ASSERT_EQ(per_node.size(), 1U);
  EXPECT_EQ(per_node[0], all);
  // The paced source with one node bypasses the merge: the same words as without nodes.
  sim::PacedSource plain{{.seed = 9}, 1e12};
  sim::PacedSource one{{.seed = 9}, 1e12, NodeLayout::contiguous(1)};
  std::vector<std::uint64_t> a(4096), b(4096);
  std::size_t got_a = 0;
  std::size_t got_b = 0;
  while (got_a == 0) {
    got_a = plain(a);
  }
  while (got_b < got_a) {
    got_b += one(std::span{b}.subspan(got_b, got_a - got_b));
  }
  a.resize(got_a);
  b.resize(got_b);
  EXPECT_EQ(a, b);
}

TEST(NodeMerge, SubtractsEachOffsetAndMergesInTimeOrder) {
  // REQ: SRS-MRG-006
  NodeMerge m{{Picoseconds{1'000}, Picoseconds{-500}}};
  const std::vector<Single> a{at(1'100, 1), at(1'300, 2)};  // true 100, 300
  const std::vector<Single> b{at(-300, 3), at(-250, 4)};    // true 200, 250
  m.push(0, a);
  std::vector<Single> out;
  m.drain(out);
  EXPECT_TRUE(out.empty()) << "node 1 has not reported";
  m.push(1, b);
  m.drain(out);
  // Node 0 has reported 300, node 1 250: everything before 250 is released.
  ASSERT_EQ(out.size(), 2U);
  EXPECT_EQ(out[0].time, Picoseconds{100});
  EXPECT_EQ(out[1].time, Picoseconds{200});
  m.advance(1, Picoseconds{-100});  // node 1 is past true time 400; node 0 is still at 300
  m.drain(out);
  ASSERT_EQ(out.size(), 3U);
  EXPECT_EQ(out[2].time, Picoseconds{250});
  m.advance(0, Picoseconds{1'350});  // node 0 is past true time 350
  m.drain(out);
  ASSERT_EQ(out.size(), 4U);
  EXPECT_EQ(out[3].time, Picoseconds{300});
  EXPECT_EQ(m.held(), 0U);
}

TEST(NodeMerge, HoldsEverythingForASlowNodeUntilItReportsOrEnds) {
  // REQ: SRS-MRG-006
  NodeMerge m{{Picoseconds{0}, Picoseconds{0}, Picoseconds{0}}};
  std::vector<Single> out;
  m.push(0, std::vector<Single>{at(10, 1), at(1'000'000'000, 1)});
  m.push(1, std::vector<Single>{at(20, 2), at(2'000'000'000, 2)});
  m.drain(out);
  EXPECT_TRUE(out.empty()) << "node 2 is silent: no max_skew lets the others run ahead";
  m.advance(2, Picoseconds{15});
  m.drain(out);
  ASSERT_EQ(out.size(), 1U);
  m.end(2);
  m.drain(out);
  EXPECT_EQ(out.size(), 2U)
      << "node 2 ended: what is earlier than both other nodes' times is released";
  m.flush(out);
  EXPECT_EQ(out.size(), 4U);
  EXPECT_EQ(m.stats().late, 0U);
}

TEST(NodeMerge, CountsALateSingleNeverDropsItSilently) {
  // REQ: SRS-MRG-006
  NodeMerge m{{Picoseconds{0}, Picoseconds{100}}};
  std::vector<Single> out;
  m.push(0, std::vector<Single>{at(1'000, 1)});
  m.advance(1, Picoseconds{2'100});  // node 1 promises nothing before true 2000 ...
  m.drain(out);
  m.push(1, std::vector<Single>{at(600, 2)});  // ... then sends true 500, broken promise
  m.flush(out);
  EXPECT_EQ(m.stats().singles_in, m.stats().singles_out + m.stats().late + m.stats().out_of_order);
  EXPECT_EQ(m.stats().late + m.stats().out_of_order, 1U);
  EXPECT_THROW(NodeMerge{{}}, std::invalid_argument);
  EXPECT_THROW(m.end(2), std::out_of_range);  // no such node (coverage review of 2.2.0)
}

// [snippet:oracle]
TEST(NodeMerge, MergedCoincidencesEqualTheSingleNodeOracle) {
  // REQ: SRS-MRG-007
  std::mt19937_64 rng{2026};
  for (int c = 0; c < 60; ++c) {
    const std::uint64_t seed = rng();
    const auto layout = random_layout(rng);
    SCOPED_TRACE("case " + std::to_string(c) + ", seed " + std::to_string(seed) + ", " +
                 std::to_string(layout.nodes()) + " nodes");
    const auto all = singles(30'000, seed, 5e6 + static_cast<double>(rng() % 40) * 1e6);
    MergerStats stats;
    const auto out = merged(all, layout, rng, &stats);
    ASSERT_EQ(out.size(), all.size());
    EXPECT_EQ(stats.late, 0U);
    EXPECT_EQ(stats.out_of_order, 0U);
    // In time order; equal times from one node keep that node's order (SRS-MRG-005).
    EXPECT_TRUE(std::is_sorted(out.begin(), out.end(),
                               [](const Single& a, const Single& b) { return a.time < b.time; }));
    const auto want = coincidences(all);
    ASSERT_FALSE(want.empty());
    EXPECT_EQ(coincidences(out), want);
  }
}
// [/snippet:oracle]

TEST(NodeMerge, TheMultiNodeSourceGivesTheOraclesCoincidences) {
  // REQ: SRS-MRG-007, SRS-SIM-025
  for (std::size_t n : {2U, 4U, 8U}) {
    SCOPED_TRACE(std::to_string(n) + " nodes");
    std::vector<Picoseconds> offsets(n);
    for (std::size_t k = 0; k < n; ++k) {
      offsets[k] =
          Picoseconds{static_cast<std::int64_t>(k % 2 == 0 ? k * 125'000 : -(k * 125'000))};
    }
    sim::MultiNodeSource src{{.seed = 11}, NodeLayout::contiguous(n, offsets)};
    std::vector<Single> out(40'000);
    for (std::size_t i = 0; i < out.size(); i += 1'000) {
      src.generate(std::span{out}.subspan(i, 1'000));
    }
    const auto all = singles(out.size(), 11, 10e6);
    EXPECT_EQ(src.merge().stats().late, 0U);
    // The same singles in the same time order; ties may differ in order.
    auto a = all;
    auto b = out;
    std::stable_sort(a.begin(), a.end(), TimeOrder{});
    std::stable_sort(b.begin(), b.end(), TimeOrder{});
    // `out` stops 40 000 singles into the merged stream, `all` 40 000 into the generated one: the
    // same singles.
    EXPECT_EQ(a, b);
    EXPECT_EQ(coincidences(out), coincidences(all));
  }
}

// The source stage of a run configured with several nodes delivers the merged
// stream: the same words, decoded, as the oracle's singles in time order.
TEST(NodeMerge, AConfigurationWithNodesFeedsTheSourceStageTheMergedStream) {
  // REQ: SRS-CFG-017, SRS-MRG-006
  const auto cfg = config::parse_config(R"({"schema_version": "2.2", "source": {"type": "synthetic",
      "rate_hz": 1e9, "seed": 4, "nodes": {"count": 3, "clock_offsets_ps": [250000, -400000, 0]}}})");
  ASSERT_TRUE(cfg.has_value()) << config::format_errors(cfg.error());
  std::string error;
  const auto detector = control::make_default_detector(*cfg, error);
  ASSERT_NE(detector, nullptr) << error;
  EXPECT_NE(detector->describe().find("3 readout nodes"), std::string::npos)
      << detector->describe();
  std::vector<std::uint64_t> words(20'000);
  std::size_t got = 0;
  while (got < words.size()) {
    got += detector->read(std::span{words}.subspan(got));
  }
  std::vector<Single> decoded(words.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  decoded.resize(dec.decode(words, decoded));
  ASSERT_EQ(decoded.size(), words.size());
  EXPECT_TRUE(std::is_sorted(decoded.begin(), decoded.end(),
                             [](const Single& a, const Single& b) { return a.time < b.time; }));
  // Without the offsets' correction a node 400 ns early would put singles out of order.
  sim::SyntheticSource plain{{.rate_hz = 1e9, .pair_fraction = 0.3, .seed = 4}};
  std::vector<std::uint64_t> expected(words.size());
  plain.generate(expected);
  std::vector<Single> want(expected.size());
  packed::StreamDecoder dec2{ScannerGeometry::num_crystals};
  want.resize(dec2.decode(expected, want));
  EXPECT_EQ(coincidences(decoded), coincidences(want));
}
