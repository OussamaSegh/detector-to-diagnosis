// SPDX-License-Identifier: MIT
// Exercise 18.5, a solution: one test per surviving mutant of the sequence tracker. MiniDAQ's own
// tracker tests left seven; each is a gap (survivors.json argues for none), and each test below
// names the mutant it kills. They are written from the class comment, not from the mutants: the
// mutant only says where to look.
#include <gtest/gtest.h>

#include <cstdint>
#include <span>
#include <vector>

#include "minidaq/format/readout_packet.hpp"

using namespace minidaq;
using namespace minidaq::readout;

namespace {

std::vector<std::byte> packet(std::uint32_t seq, std::uint64_t word) {
  const std::vector<std::uint64_t> words{word};
  std::vector<std::byte> out(header_bytes + word_bytes);
  PacketHeader h;
  h.sequence = seq;
  h.word_count = 1;
  EXPECT_EQ(encode_packet(h, words, out), out.size());
  return out;
}

// Feeds packets to a tracker and records the word of each delivered packet.
struct Harness {
  SequenceTracker tracker;
  std::vector<std::uint64_t> delivered;
  std::int64_t now = 0;
  explicit Harness(TrackerConfig c = {}) : tracker{c} {}
  auto sink() {
    return [this](const PacketHeader&, std::span<const std::byte> payload) {
      delivered.push_back(payload_word(payload, 0));
    };
  }
  void offer(std::uint32_t seq) {
    const auto d = packet(seq, seq);
    const auto p = parse_packet(d);
    ASSERT_TRUE(p);
    tracker.offer(*p, now, sink());
  }
};

}  // namespace

// [snippet:hold]
// Mutants 259 (`held_ == 0` negated or turned into `!=`): the hold clock must start with the
// first packet held behind a gap and not move when more packets are held.
TEST(TrackerMutants, TheHoldTimeCountsFromTheFirstPacketHeld) {
  Harness h{TrackerConfig{64, 1'000'000}};
  h.offer(0);
  h.now = 10;
  h.offer(2);  // 1 is missing: the clock starts at 10
  h.now = 900'000;
  h.offer(3);  // held too, but the gap is as old as before
  h.now = 1'000'010;
  h.tracker.expire(h.now, h.sink());
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 2, 3}));
  EXPECT_EQ(h.tracker.stats().lost, 1U);
}
// [/snippet:hold]

// Mutants 279 and 283 (the clock not restarted, or restarted from unused slots): when a gap
// closes and another remains, its clock starts from the earliest packet still held.
TEST(TrackerMutants, AfterAGapClosesTheNextGapsClockStartsFromItsOwnPackets) {
  Harness h{TrackerConfig{64, 1'000'000}};
  h.offer(0);
  h.now = 10;
  h.offer(2);  // gap at 1
  h.now = 500'000;
  h.offer(4);  // gap at 3, behind a packet that arrived at 500'000
  h.now = 600'000;
  h.offer(1);  // the first gap closes: 1 and 2 leave, 4 waits for 3
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2}));
  h.now = 1'200'000;  // 1.19 ms after the first packet held, 0.7 ms after packet 4
  h.tracker.expire(h.now, h.sink());
  EXPECT_EQ(h.tracker.stats().lost, 0U) << "gap 3 has waited only 0.7 ms";
  h.now = 1'500'000;
  h.tracker.expire(h.now, h.sink());
  EXPECT_EQ(h.tracker.stats().lost, 1U);
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2, 4}));
}

// Mutant 300 (`now_ns - oldest_held_ns_` turned into `+`): a gap is lost when it has waited
// max_hold_ns, measured from when its first packet was held, not from time zero.
TEST(TrackerMutants, AGapHeldLateInTheRunWaitsTheFullHoldTime) {
  Harness h{TrackerConfig{64, 1'000'000}};
  h.now = 5'000'000;
  h.offer(0);
  h.offer(2);
  h.now = 5'500'000;
  h.tracker.expire(h.now, h.sink());
  EXPECT_EQ(h.tracker.stats().lost, 0U);
  h.now = 6'000'000;
  h.tracker.expire(h.now, h.sink());
  EXPECT_EQ(h.tracker.stats().lost, 1U);
}

// Mutant 211 (`ahead > max_gap_packets` turned into `>=`): a jump of exactly the maximum gap is
// still loss, not a restart.
TEST(TrackerMutants, AJumpOfExactlyTheMaximumGapIsLoss) {
  Harness h{TrackerConfig{64, 1'000'000, 1000}};
  h.offer(10);
  h.offer(11 + 1000);  // 1000 ahead of the 11 it waits for
  EXPECT_EQ(h.tracker.stats().resyncs, 0U);
  EXPECT_EQ(h.tracker.stats().lost, 1000U - 63U) << "the last 63 may still arrive";
  h.offer(11 + 1001 + 1001);  // 1001 ahead of 1012: a restart
  EXPECT_EQ(h.tracker.stats().resyncs, 1U);
}
