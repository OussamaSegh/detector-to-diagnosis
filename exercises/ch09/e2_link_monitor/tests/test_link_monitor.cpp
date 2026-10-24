// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "link_monitor.hpp"
#include "minidaq/format/readout_packet.hpp"
#include "minidaq/sim/readout_link.hpp"

using namespace ex92;

namespace {

LinkCounts run(std::initializer_list<std::uint16_t> seqs) {
  LinkMonitor m;
  for (auto s : seqs) {
    m.on_packet(s);
  }
  return m.counts();
}

// The 16 low bits of each packet's sequence number, after the link's damage:
// a board with a 16-bit counter.
std::vector<std::uint16_t> faulty_link(std::size_t packets, minidaq::sim::LinkFaultConfig f,
                                       minidaq::sim::LinkFaultCounts& injected) {
  std::vector<std::uint64_t> words(packets);
  minidaq::sim::Packetizer pk{{.source = 0, .first_sequence = 60'000, .words_per_packet = 1}};
  auto dgrams = pk.packetize(words, false);
  minidaq::sim::LinkFaults faults{f};
  faults.apply(dgrams);
  injected = faults.counts();
  std::vector<std::uint16_t> seqs;
  for (const auto& d : dgrams) {
    seqs.push_back(static_cast<std::uint16_t>(d.sequence));
  }
  return seqs;
}

}  // namespace

TEST(LinkMonitor, CleanLink) {
  const auto c = run({10, 11, 12, 13});
  EXPECT_EQ(c.received, 4U);
  EXPECT_EQ(c.lost + c.reordered + c.duplicates, 0U);
}

TEST(LinkMonitor, Loss) {
  const auto c = run({10, 11, 14, 15});
  EXPECT_EQ(c.lost, 2U);
}

TEST(LinkMonitor, ReorderingIsNotLoss) {
  const auto c = run({10, 12, 11, 13});
  EXPECT_EQ(c.lost, 0U) << "11 was late, not lost";
  EXPECT_EQ(c.reordered, 1U);
}

TEST(LinkMonitor, Duplicates) {
  const auto c = run({10, 11, 11, 12, 11});
  EXPECT_EQ(c.duplicates, 2U);
  EXPECT_EQ(c.lost, 0U);
}

TEST(LinkMonitor, AcrossTheWrap) {
  const auto c = run({65533, 65534, 65535, 0, 1, 3, 2});
  EXPECT_EQ(c.lost, 0U);
  EXPECT_EQ(c.reordered, 1U);
  const auto d = run({65534, 1});
  EXPECT_EQ(d.lost, 2U) << "65535 and 0 are missing";
}

TEST(LinkMonitor, MatchesTheInjectedLossAndReordering) {
  // 200,000 packets: the 16-bit counter wraps three times.
  minidaq::sim::LinkFaultCounts injected;
  const auto seqs = faulty_link(200'000, {.loss = 0.001, .reorder = 0.002, .max_displacement = 8, .seed = 3},
                                injected);
  LinkMonitor m;
  for (auto s : seqs) {
    m.on_packet(s);
  }
  EXPECT_GT(injected.lost, 100U);
  EXPECT_GT(injected.delayed, 200U);
  EXPECT_EQ(m.counts().lost, injected.lost);
  EXPECT_EQ(m.counts().reordered, injected.delayed);
  EXPECT_EQ(m.counts().duplicates, 0U);
}

TEST(LinkMonitor, MatchesTheInjectedDuplicates) {
  minidaq::sim::LinkFaultCounts injected;
  const auto seqs = faulty_link(200'000, {.loss = 0.001, .duplicate = 0.001, .seed = 5}, injected);
  LinkMonitor m;
  for (auto s : seqs) {
    m.on_packet(s);
  }
  EXPECT_GT(injected.duplicated, 100U);
  EXPECT_EQ(m.counts().duplicates, injected.duplicated);
  EXPECT_EQ(m.counts().lost, injected.lost);
}
