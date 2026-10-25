// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

#include "minidaq/format/readout_packet.hpp"
#include "minidaq/sim/readout_link.hpp"

using namespace minidaq;
using namespace minidaq::readout;

namespace {

std::vector<std::byte> packet(std::uint32_t seq, std::vector<std::uint64_t> words, std::uint8_t flags = 0) {
  std::vector<std::byte> out(header_bytes + words.size() * word_bytes);
  PacketHeader h;
  h.flags = flags;
  h.source = 3;
  h.sequence = seq;
  h.word_count = static_cast<std::uint16_t>(words.size());
  EXPECT_EQ(encode_packet(h, words, out), out.size());
  return out;
}

// Feeds datagrams to a tracker and records the first word of each delivered packet.
struct Harness {
  SequenceTracker tracker;
  std::vector<std::uint64_t> delivered;
  std::int64_t now = 0;
  explicit Harness(TrackerConfig c = {}) : tracker{c} {}
  void offer(const std::vector<std::byte>& d) {
    auto p = parse_packet(d);
    ASSERT_TRUE(p);
    tracker.offer(*p, now, [&](const PacketHeader&, std::span<const std::byte> payload) {
      delivered.push_back(payload_word(payload, 0));
    });
  }
  void expire() {
    tracker.expire(now, [&](const PacketHeader&, std::span<const std::byte> payload) {
      delivered.push_back(payload_word(payload, 0));
    });
  }
};

}  // namespace

TEST(ReadoutPacket, RoundTrip) {
  // REQ: SRS-RDO-001
  const std::vector<std::uint64_t> words{0x0123456789ABCDEFULL, 0, ~0ULL};
  const auto d = packet(0xFFFFFFFEU, words, flag_end_of_stream);
  ASSERT_EQ(d.size(), 16U + 24U);
  EXPECT_EQ(d[0], std::byte{'M'});
  EXPECT_EQ(d[8], std::byte{0xFE});  // little-endian sequence
  const auto p = parse_packet(d);
  ASSERT_TRUE(p);
  EXPECT_EQ(p->header.sequence, 0xFFFFFFFEU);
  EXPECT_EQ(p->header.source, 3);
  EXPECT_EQ(p->header.flags, flag_end_of_stream);
  ASSERT_EQ(p->header.word_count, 3);
  for (std::size_t i = 0; i < words.size(); ++i) {
    EXPECT_EQ(payload_word(p->payload, i), words[i]);
  }
  EXPECT_EQ(words_per_standard_mtu, 182U);  // 16 + 182 * 8 = 1472 bytes of UDP payload
}

TEST(ReadoutPacket, RejectsEveryMalformedField) {
  // REQ: SRS-RDO-002
  const auto good = packet(7, {1, 2});
  auto expect = [](std::vector<std::byte> d, PacketError e) {
    const auto p = parse_packet(d);
    ASSERT_FALSE(p);
    EXPECT_EQ(p.error(), e) << to_string(p.error());
  };
  expect({good.begin(), good.begin() + 15}, PacketError::too_short);
  auto d = good;
  d[3] = std::byte{'X'};
  expect(d, PacketError::bad_magic);
  d = good;
  d[4] = std::byte{2};
  expect(d, PacketError::bad_version);
  d = good;
  d[5] = std::byte{0x02};
  expect(d, PacketError::bad_flags);
  d = good;
  d[12] = std::byte{0};
  d[13] = std::byte{0};
  expect(d, PacketError::bad_word_count);
  d = good;
  d[12] = std::byte{3};  // claims 3 words, carries 2
  expect(d, PacketError::bad_length);
  d = good;
  d.push_back(std::byte{0});  // one byte too many
  expect(d, PacketError::bad_length);
  d = good;
  d[15] = std::byte{1};
  expect(d, PacketError::bad_reserved);
  std::vector<std::byte> small(20);
  EXPECT_EQ(encode_packet({}, std::vector<std::uint64_t>{1}, small), 0U) << "output too small";
  EXPECT_EQ(encode_packet({}, std::vector<std::uint64_t>(max_words + 1), small), 0U) << "too many words";
}

// [snippet:table]
// Table-driven: one row per malformed header, each run and reported as a test
// of its own (ReadoutPacketHeaders/MalformedHeader.IsRejected/bad_flags_0x80).
struct HeaderCase {
  const char* name;
  std::size_t offset;  // byte of the header to overwrite
  std::uint8_t value;
  PacketError expected;
};

class MalformedHeader : public ::testing::TestWithParam<HeaderCase> {};

TEST_P(MalformedHeader, IsRejected) {
  // REQ: SRS-RDO-002
  const HeaderCase& c = GetParam();
  auto d = packet(7, {1, 2});
  d[c.offset] = std::byte{c.value};
  const auto p = parse_packet(d);
  ASSERT_FALSE(p);
  EXPECT_EQ(p.error(), c.expected) << to_string(p.error());
}

INSTANTIATE_TEST_SUITE_P(
    ReadoutPacketHeaders, MalformedHeader,
    ::testing::Values(HeaderCase{"magic_0", 0, 'X', PacketError::bad_magic},
                      HeaderCase{"magic_3", 3, 'r', PacketError::bad_magic},
                      HeaderCase{"version_0", 4, 0, PacketError::bad_version},
                      HeaderCase{"version_2", 4, 2, PacketError::bad_version},
                      HeaderCase{"version_255", 4, 255, PacketError::bad_version},
                      HeaderCase{"flags_0x02", 5, 0x02, PacketError::bad_flags},
                      HeaderCase{"flags_0x04", 5, 0x04, PacketError::bad_flags},
                      HeaderCase{"flags_0x08", 5, 0x08, PacketError::bad_flags},
                      HeaderCase{"flags_0x10", 5, 0x10, PacketError::bad_flags},
                      HeaderCase{"flags_0x20", 5, 0x20, PacketError::bad_flags},
                      HeaderCase{"flags_0x40", 5, 0x40, PacketError::bad_flags},
                      HeaderCase{"flags_0x80", 5, 0x80, PacketError::bad_flags},
                      HeaderCase{"word_count_high_byte", 13, 0x04, PacketError::bad_word_count},
                      HeaderCase{"reserved_14", 14, 1, PacketError::bad_reserved},
                      HeaderCase{"reserved_15", 15, 0x80, PacketError::bad_reserved}),
    [](const ::testing::TestParamInfo<HeaderCase>& row) { return std::string{row.param.name}; });
// [/snippet:table]

TEST(ReadoutPacket, SequenceDistanceAcrossTheWrap) {
  // REQ: SRS-RDO-003
  EXPECT_EQ(sequence_distance(10, 12), 2);
  EXPECT_EQ(sequence_distance(12, 10), -2);
  EXPECT_EQ(sequence_distance(0xFFFFFFFFU, 0), 1);
  EXPECT_EQ(sequence_distance(0, 0xFFFFFFFFU), -1);
  EXPECT_EQ(sequence_distance(0xFFFFFFF0U, 5), 21);
}

TEST(SequenceTracker, InOrderIsDeliveredAtOnce) {
  // REQ: SRS-RDO-004
  Harness h;
  for (std::uint64_t i = 0; i < 10; ++i) {
    h.offer(packet(static_cast<std::uint32_t>(100 + i), {i}));
  }
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2, 3, 4, 5, 6, 7, 8, 9}));
  EXPECT_EQ(h.tracker.stats().delivered, 10U);
  EXPECT_EQ(h.tracker.stats().lost + h.tracker.stats().reordered + h.tracker.stats().stale, 0U);
  EXPECT_EQ(h.tracker.stats().words, 10U);
}

TEST(SequenceTracker, ReorderedPacketsLeaveInSequenceOrder) {
  // REQ: SRS-RDO-004
  Harness h;
  for (std::uint32_t s : {0U, 2U, 3U, 1U, 4U}) {
    h.offer(packet(s, {s}));
  }
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2, 3, 4}));
  EXPECT_EQ(h.tracker.stats().reordered, 1U) << "only 1 arrived out of order; 2 and 3 merely waited for it";
  EXPECT_EQ(h.tracker.stats().lost, 0U);
  EXPECT_EQ(h.tracker.held(), 0U);
}

TEST(SequenceTracker, AGapIsDeclaredLostAfterTheHoldTime) {
  // REQ: SRS-RDO-005
  Harness h{TrackerConfig{64, 1'000'000}};
  h.offer(packet(0, {0}));
  h.now = 10;
  h.offer(packet(2, {2}));  // 1 is missing
  h.now = 999'000;
  h.expire();
  EXPECT_EQ(h.delivered.size(), 1U) << "still waiting for 1";
  h.now = 1'000'010;
  h.expire();
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 2}));
  EXPECT_EQ(h.tracker.stats().lost, 1U);
  h.offer(packet(1, {1}));  // arrives after its gap was closed
  EXPECT_EQ(h.tracker.stats().stale, 1U);
  EXPECT_EQ(h.delivered.size(), 2U) << "a stale packet is never delivered: its words would be out of order";
}

TEST(SequenceTracker, AFullWindowDeclaresTheOldestGapLost) {
  // REQ: SRS-RDO-005
  Harness h{TrackerConfig{4, 1'000'000'000}};
  h.offer(packet(0, {0}));
  for (std::uint32_t s = 2; s <= 5; ++s) {  // 1 missing; 2..4 fit, 5 does not
    h.offer(packet(s, {s}));
  }
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 2, 3, 4, 5}));
  EXPECT_EQ(h.tracker.stats().lost, 1U);
}

TEST(SequenceTracker, ALargeJumpIsCountedInOneStep) {
  // REQ: SRS-RDO-005
  Harness h;
  h.offer(packet(0, {0}));
  h.offer(packet(1'000'001, {1}));  // a million packets missing
  EXPECT_EQ(h.tracker.stats().lost, 1'000'000U - 63U) << "the last 63 may still arrive";
  h.now = 2'000'000;
  h.expire();
  EXPECT_EQ(h.tracker.stats().lost, 1'000'000U);
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1}));
}

TEST(SequenceTracker, DuplicatesAreStale) {
  // REQ: SRS-RDO-005
  Harness h;
  h.offer(packet(0, {0}));
  h.offer(packet(0, {0}));  // duplicate of a delivered packet
  h.offer(packet(2, {2}));
  h.offer(packet(2, {2}));  // duplicate of a held packet
  h.offer(packet(1, {1}));
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2}));
  EXPECT_EQ(h.tracker.stats().stale, 2U);
}

// A copy of a held packet that arrives after a higher sequence number is stale,
// not reordered: only a packet that is used counts as reordered (MDQ-PR-019).
TEST(SequenceTracker, ALateCopyOfAHeldPacketIsNotReordered) {
  // REQ: SRS-RDO-005, SRS-RDO-007
  Harness h;
  h.offer(packet(0, {0}));
  h.offer(packet(2, {2}));  // early: held
  h.offer(packet(3, {3}));  // early: held
  h.offer(packet(2, {2}));  // a copy of 2, after 3: stale
  EXPECT_EQ(h.tracker.stats().reordered, 0U);
  h.offer(packet(1, {1}));  // overtaken by 2 and 3, and used
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{0, 1, 2, 3}));
  EXPECT_EQ(h.tracker.stats().reordered, 1U);
  EXPECT_EQ(h.tracker.stats().stale, 1U);
}

TEST(SequenceTracker, WorksAcrossTheSequenceWrap) {
  // REQ: SRS-RDO-003
  Harness h;
  std::vector<std::uint32_t> order;
  for (std::uint32_t i = 0; i < 20; ++i) {
    order.push_back(0xFFFFFFF6U + i);  // ...FFF6 .. 9, wrapping after ...FFFF
  }
  std::swap(order[9], order[10]);  // reorder exactly at the wrap
  for (std::uint32_t s : order) {
    h.offer(packet(s, {s}));
  }
  ASSERT_EQ(h.delivered.size(), 20U);
  for (std::size_t i = 0; i < 20; ++i) {
    EXPECT_EQ(h.delivered[i], static_cast<std::uint32_t>(0xFFFFFFF6U + i));
  }
  EXPECT_EQ(h.tracker.stats().lost, 0U);
  EXPECT_EQ(h.tracker.stats().reordered, 1U);
}

TEST(SequenceTracker, ASourceThatRestartsIsFollowedAfterARunOfStalePackets) {
  // REQ: SRS-RDO-006
  Harness h{TrackerConfig{4, 1'000'000}};
  for (std::uint32_t s = 1000; s < 1010; ++s) {
    h.offer(packet(s, {s}));
  }
  for (std::uint32_t s = 0; s < 10; ++s) {  // the board was reset: numbering starts again
    h.offer(packet(s, {s}));
  }
  EXPECT_EQ(h.tracker.stats().resyncs, 1U);
  EXPECT_EQ(h.tracker.stats().stale, 4U) << "a window's worth is dropped before the tracker believes it";
  EXPECT_EQ(h.delivered.size(), 10U + 6U);
  EXPECT_EQ(h.delivered.back(), 9U);
}

TEST(SequenceTracker, AJumpBeyondTheMaximumGapIsARestart) {
  // REQ: SRS-RDO-006
  // Found by fuzz_packet: a jump of about 2^31 sits where serial arithmetic
  // is undefined, and was counted as two billion lost packets.
  Harness h;
  h.offer(packet(10, {10}));
  h.offer(packet(0x8000000AU, {11}));  // 2^31 ahead
  h.offer(packet(0x8000000BU, {12}));
  EXPECT_EQ(h.tracker.stats().resyncs, 1U);
  EXPECT_EQ(h.tracker.stats().lost, 0U);
  EXPECT_EQ(h.delivered, (std::vector<std::uint64_t>{10, 11, 12}));
  h.offer(packet(0x8000000BU + (1U << 23), {13}));  // 8 M ahead: loss, within the maximum gap
  EXPECT_EQ(h.tracker.stats().resyncs, 1U);
  EXPECT_EQ(h.tracker.stats().lost, (1U << 23) - 64U);
}

TEST(SequenceTracker, RejectsAWindowThatIsNotAPowerOfTwo) {
  // REQ: SRS-RDO-004
  auto make = [](std::size_t window) { return SequenceTracker{TrackerConfig{window, 1000}}; };
  EXPECT_THROW((void)make(100), std::invalid_argument);
  EXPECT_THROW((void)make(0), std::invalid_argument);
  EXPECT_NO_THROW((void)make(128));
}

// The fault injector and the tracker together: every packet is accounted for.
TEST(SequenceTracker, AccountsForEveryPacketThroughAFaultyLink) {
  // REQ: SRS-RDO-007
  std::vector<std::uint64_t> words(200'000);
  std::iota(words.begin(), words.end(), std::uint64_t{0});
  sim::Packetizer pk{{.source = 3, .first_sequence = 0xFFFFF000U, .words_per_packet = 100}};
  auto packets = pk.packetize(words, true);
  ASSERT_EQ(packets.size(), 2000U);
  sim::LinkFaults faults{{.loss = 0.01, .reorder = 0.02, .max_displacement = 8, .duplicate = 0.005, .seed = 9}};
  faults.apply(packets);
  const auto& f = faults.counts();
  EXPECT_GT(f.lost, 5U);
  EXPECT_GT(f.delayed, 15U);
  EXPECT_GT(f.duplicated, 2U);

  SequenceTracker t;
  std::vector<std::uint64_t> out;
  auto deliver = [&](const PacketHeader& h, std::span<const std::byte> payload) {
    for (std::size_t i = 0; i < h.word_count; ++i) {
      out.push_back(payload_word(payload, i));
    }
  };
  for (const auto& d : packets) {
    auto p = parse_packet(d.bytes);
    ASSERT_TRUE(p);
    t.offer(*p, 0, deliver);
  }
  t.flush(deliver);
  const auto& s = t.stats();
  EXPECT_EQ(s.lost, f.lost) << "with max_displacement < window, only real losses are declared lost";
  EXPECT_EQ(s.stale, f.duplicated);
  EXPECT_EQ(s.delivered, 2000U - f.lost);
  EXPECT_EQ(s.received, s.delivered + s.stale);
  EXPECT_TRUE(std::is_sorted(out.begin(), out.end())) << "words leave in order";
  EXPECT_GT(s.reordered, 0U);
  EXPECT_LE(s.reordered, f.delayed) << "only delayed packets arrive out of order";
  EXPECT_EQ(out.size(), 200'000U - 100U * f.lost);
}
