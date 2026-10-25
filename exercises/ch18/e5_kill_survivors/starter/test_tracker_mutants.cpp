// SPDX-License-Identifier: MIT
// Exercise 18.5, the starter: a place for the tests that kill the sequence tracker's surviving
// mutants. MiniDAQ's own tracker tests (SequenceTracker.* and the tracker property) run with these
// in every mutation run; add a test here for each survivor that is not equivalent.
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

TEST(TrackerMutants, APacketInOrderIsDeliveredAtOnce) {
  Harness h;
  h.offer(7);
  EXPECT_EQ(h.delivered, std::vector<std::uint64_t>{7});
}
