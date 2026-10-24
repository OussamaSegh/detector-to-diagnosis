// SPDX-License-Identifier: MIT
// Fuzz target: the MDQ-R1 packet parser and the sequence tracker (Chapter 9).
//
// The input is a series of datagrams, each preceded by one byte of length and
// one byte of arrival time (in steps of 100 us). Properties checked for any
// input: the parser never reads outside the datagram; an accepted packet
// re-encodes to exactly the same bytes; every packet offered to the tracker is
// delivered or counted stale; delivered sequence numbers increase (between
// resyncs) by at most the maximum gap; the words delivered are the words of the delivered packets.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>
#include <vector>

#include "minidaq/format/readout_packet.hpp"

using namespace minidaq;

namespace {

void check(bool ok) {
  if (!ok) {
    std::abort();  // libFuzzer reports the input that got here
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  constexpr std::uint32_t window = 8;
  constexpr std::uint32_t max_gap = 1U << 16;
  readout::SequenceTracker tracker{readout::TrackerConfig{window, 1'000'000, max_gap}};
  std::int64_t now = 0;
  std::uint64_t delivered_words = 0;
  std::uint64_t offered_words = 0;
  std::uint64_t last_resyncs = 0;
  bool have_last = false;
  std::uint32_t last_seq = 0;
  auto deliver = [&](const readout::PacketHeader& h, std::span<const std::byte> payload) {
    check(payload.size() == std::size_t{h.word_count} * readout::word_bytes);
    if (tracker.stats().resyncs != last_resyncs) {
      have_last = false;  // a new numbering starts
      last_resyncs = tracker.stats().resyncs;
    }
    if (have_last) {
      const std::int32_t step = readout::sequence_distance(last_seq, h.sequence);
      check(step > 0 && step <= static_cast<std::int32_t>(max_gap + window));
    }
    have_last = true;
    last_seq = h.sequence;
    delivered_words += h.word_count;
  };

  std::size_t pos = 0;
  while (pos + 2 <= size) {
    const std::size_t len = data[pos];
    now += std::int64_t{data[pos + 1]} * 100'000;
    pos += 2;
    const std::size_t n = std::min(len, size - pos);
    // A copy of exactly n bytes, so that ASan catches any read past the datagram.
    const std::vector<std::byte> d(reinterpret_cast<const std::byte*>(data + pos),
                                   reinterpret_cast<const std::byte*>(data + pos + n));
    pos += n;
    const auto p = readout::parse_packet(d);
    if (!p) {
      continue;
    }
    check(p->payload.size() == std::size_t{p->header.word_count} * readout::word_bytes);
    std::vector<std::uint64_t> words(p->header.word_count);
    for (std::size_t i = 0; i < words.size(); ++i) {
      words[i] = readout::payload_word(p->payload, i);
    }
    std::vector<std::byte> again(d.size());
    check(readout::encode_packet(p->header, words, again) == d.size());
    check(again == d);  // lossless: nothing in a valid packet is ignored
    offered_words += p->header.word_count;
    tracker.offer(*p, now, deliver);
    tracker.expire(now, deliver);
  }
  tracker.flush(deliver);
  const auto& s = tracker.stats();
  check(tracker.held() == 0);
  check(s.received == s.delivered + s.stale);
  check(s.words == delivered_words);
  check(delivered_words <= offered_words);
  return 0;
}
