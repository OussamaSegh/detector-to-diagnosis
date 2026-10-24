// SPDX-License-Identifier: MIT
// MiniDAQ - the readout packet, format MDQ-R1, and the sequence tracker that
// turns a stream of datagrams back into an ordered stream of words (Chapter 9).
//
// One UDP datagram carries one packet: a 16-byte header followed by
// word_count MDQ-P1 words (packed_single.hpp). All fields are little-endian.
//
//  offset  size  field
//       0     4  magic        "MDQR" (0x4D 0x44 0x51 0x52)
//       4     1  version      1
//       5     1  flags        bit 0: end of stream; other bits must be 0
//       6     2  source       which readout link sent it (board or concentrator id)
//       8     4  sequence     per source, +1 per packet, wraps from 2^32 - 1 to 0
//      12     2  word_count   1 .. max_words
//      14     2  reserved     must be 0
//      16  8*n   words        MDQ-P1, time-ordered within the source
//
// The datagram length must be exactly 16 + 8 * word_count. With a standard
// 1500-byte Ethernet MTU (1472 bytes of UDP payload over IPv4) a packet holds
// at most 182 words; jumbo frames allow up to max_words.
#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <string_view>
#include <vector>

#include "minidaq/core/expected.hpp"

namespace minidaq::readout {

// [snippet:header]
inline constexpr std::array<std::byte, 4> magic{std::byte{'M'}, std::byte{'D'}, std::byte{'Q'}, std::byte{'R'}};
inline constexpr std::uint8_t version = 1;
inline constexpr std::size_t header_bytes = 16;
inline constexpr std::size_t word_bytes = 8;
inline constexpr std::size_t max_words = 1024;                                            // 8208-byte datagram
inline constexpr std::size_t words_per_standard_mtu = (1500 - 20 - 8 - header_bytes) / word_bytes;  // 182
inline constexpr std::size_t max_packet_bytes = header_bytes + max_words * word_bytes;
inline constexpr std::uint8_t flag_end_of_stream = 0x01;

struct PacketHeader {
  std::uint8_t flags = 0;
  std::uint16_t source = 0;
  std::uint32_t sequence = 0;
  std::uint16_t word_count = 0;
  friend bool operator==(const PacketHeader&, const PacketHeader&) = default;
};
// [/snippet:header]

enum class PacketError : std::uint8_t {
  too_short,       // fewer than 16 bytes
  bad_magic,       // not an MDQ-R packet at all
  bad_version,     // a version this program does not read
  bad_flags,       // undefined flag bits set
  bad_word_count,  // 0 or more than max_words
  bad_length,      // datagram length does not match word_count
  bad_reserved,    // reserved field not 0
};
inline constexpr std::size_t num_packet_errors = 7;
[[nodiscard]] std::string_view to_string(PacketError e) noexcept;

// A parsed packet. `payload` points into the caller's datagram buffer.
struct PacketView {
  PacketHeader header;
  std::span<const std::byte> payload;  // word_count * 8 bytes
};

// Writes header and words into `out`; returns the datagram length, or 0 if
// `out` is too small or words.size() is not in 1 .. max_words.
[[nodiscard]] std::size_t encode_packet(const PacketHeader& h, std::span<const std::uint64_t> words,
                                        std::span<std::byte> out) noexcept;

// Checks every header field and the length. Never reads past `datagram`.
[[nodiscard]] Expected<PacketView, PacketError> parse_packet(std::span<const std::byte> datagram) noexcept;

// Reads word i of a payload (little-endian, alignment-free).
[[nodiscard]] std::uint64_t payload_word(std::span<const std::byte> payload, std::size_t i) noexcept;

// [snippet:serial]
// Serial number arithmetic on 32-bit sequence numbers (the idea of RFC 1982):
// the signed distance from `from` to `to`, correct across the wrap as long as
// the two are less than 2^31 apart. The conversion to int32_t is modular in
// C++20, so this is defined behavior.
[[nodiscard]] constexpr std::int32_t sequence_distance(std::uint32_t from, std::uint32_t to) noexcept {
  return static_cast<std::int32_t>(to - from);
}
// [/snippet:serial]

struct TrackerConfig {
  std::size_t window_packets = 64;      // packets held while waiting for a missing one (power of two)
  std::int64_t max_hold_ns = 1'000'000;  // a gap older than this is declared lost
  // A forward jump larger than this is not loss but a restart or a corrupted
  // counter: 2^24 packets is minutes of data at any realistic packet rate,
  // and far from the 2^31 where serial arithmetic stops being meaningful.
  std::uint32_t max_gap_packets = std::uint32_t{1} << 24;
};

// [snippet:stats]
struct TrackerStats {
  std::uint64_t received = 0;   // valid packets offered to the tracker
  std::uint64_t delivered = 0;  // packets passed on, in sequence order
  std::uint64_t reordered = 0;  // arrived after a higher sequence number, and was still used
  std::uint64_t lost = 0;       // sequence numbers declared missing
  std::uint64_t stale = 0;      // duplicates and packets that came after their gap was closed
  std::uint64_t resyncs = 0;    // the source restarted its sequence numbers
  std::uint64_t words = 0;      // words delivered
};
// [/snippet:stats]

// Restores sequence order for one source. Packets are offered as they arrive;
// the tracker delivers them, in order, to a callback. A packet that arrives
// early is held until the gap before it is filled, the window is full, or the
// gap has waited max_hold_ns; then the missing sequence numbers are counted as
// lost and delivery moves on. A packet for a sequence number that was already
// delivered or declared lost is stale: it is counted and dropped, because
// delivering it would put its words out of time order. More than
// window_packets stale packets in a row, or a jump forward of more than
// max_gap_packets, mean the source restarted (a board reset): the tracker
// delivers what it holds, counts a resync and follows the new numbering.
//
// Storage is allocated once, in the constructor; offer() and expire() do not
// allocate. Not thread-safe: one tracker per receiving thread.
class SequenceTracker {
 public:
  explicit SequenceTracker(TrackerConfig cfg = {});

  // `deliver(const PacketHeader&, std::span<const std::byte> payload)` is
  // called zero or more times, in sequence order. It is taken by value (it is
  // called many times, so there is nothing to forward); pass a lambda that
  // captures by reference.
  template <typename Deliver>
  void offer(const PacketView& p, std::int64_t now_ns, Deliver deliver);

  // Declares gaps older than max_hold_ns lost and delivers what follows them.
  // Call it when no packet has arrived for a while.
  template <typename Deliver>
  void expire(std::int64_t now_ns, Deliver deliver);

  // End of stream: everything held is delivered, remaining gaps are lost.
  template <typename Deliver>
  void flush(Deliver deliver);

  // After end of stream: the next packet starts a new stream wherever its
  // sequence number lies. Statistics are kept. Call after flush().
  void restart() noexcept { started_ = false; }

  [[nodiscard]] const TrackerStats& stats() const noexcept { return stats_; }
  [[nodiscard]] std::size_t held() const noexcept { return held_; }
  [[nodiscard]] bool started() const noexcept { return started_; }
  [[nodiscard]] std::uint32_t next_expected() const noexcept { return next_; }

 private:
  struct Slot {
    bool used = false;
    PacketHeader header;
    std::int64_t arrived_ns = 0;
    std::size_t bytes = 0;
  };
  [[nodiscard]] std::size_t index_of(std::uint32_t seq) const noexcept { return seq % cfg_.window_packets; }
  [[nodiscard]] std::span<std::byte> storage(std::size_t slot) noexcept {
    return std::span(data_).subspan(slot * slot_bytes_, slot_bytes_);
  }
  template <typename Deliver>
  void deliver_ready(Deliver& deliver);
  template <typename Deliver>
  void skip_gap(Deliver& deliver);  // declare next_ lost, move on

  TrackerConfig cfg_;
  std::size_t slot_bytes_;
  std::vector<Slot> slots_;
  std::vector<std::byte> data_;
  std::uint32_t next_ = 0;     // the sequence number we wait for
  std::uint32_t highest_ = 0;  // the highest sequence number seen
  bool started_ = false;
  std::size_t held_ = 0;
  std::size_t stale_run_ = 0;
  std::int64_t oldest_held_ns_ = 0;  // arrival of the earliest packet held behind the gap
  TrackerStats stats_;
};

// ---------------------------------------------------------------------------

// [snippet:offer]
template <typename Deliver>
void SequenceTracker::offer(const PacketView& p, std::int64_t now_ns, Deliver deliver) {
  ++stats_.received;
  const std::uint32_t seq = p.header.sequence;
  if (!started_) {
    started_ = true;  // the first packet defines where the stream starts
    next_ = seq;
    highest_ = seq;
  }
  std::int32_t ahead = sequence_distance(next_, seq);
  if (ahead < 0) {
    if (++stale_run_ <= cfg_.window_packets) {
      ++stats_.stale;  // already delivered, or declared lost: too late to use
      return;
    }
    flush(deliver);  // a run of stale packets: the source started again
    ++stats_.resyncs;
    next_ = seq;
    highest_ = seq;
    ahead = 0;
  }
  stale_run_ = 0;
  if (ahead > static_cast<std::int32_t>(cfg_.max_gap_packets)) {
    flush(deliver);  // too far ahead to be loss: a new numbering
    ++stats_.resyncs;
    next_ = seq;
    highest_ = seq;
    ahead = 0;
  }
  if (sequence_distance(seq, highest_) > 0) {
    ++stats_.reordered;  // overtaken on the way, but not too late
  } else {
    highest_ = seq;
  }
  if (ahead == 0) {
    deliver(p.header, p.payload);
    ++stats_.delivered;
    stats_.words += p.header.word_count;
    ++next_;
    deliver_ready(deliver);
    return;
  }
  // Early: make room if it lies beyond the window, then hold it. With nothing
  // held, a large gap is skipped in one step rather than one number at a time.
  const auto window = static_cast<std::int32_t>(cfg_.window_packets);
  while (sequence_distance(next_, seq) >= window) {
    if (held_ == 0) {
      const auto jump = static_cast<std::uint32_t>(sequence_distance(next_, seq) - (window - 1));
      stats_.lost += jump;
      next_ += jump;
      break;
    }
    skip_gap(deliver);
  }
  if (sequence_distance(next_, seq) == 0) {  // the gap closed while making room
    deliver(p.header, p.payload);
    ++stats_.delivered;
    stats_.words += p.header.word_count;
    ++next_;
    deliver_ready(deliver);
    return;
  }
  Slot& s = slots_[index_of(seq)];
  if (s.used) {
    ++stats_.stale;  // a duplicate of a packet already held
    return;
  }
  const std::size_t n = std::min(p.payload.size(), slot_bytes_);
  std::copy_n(p.payload.begin(), n, storage(index_of(seq)).begin());
  s = Slot{true, p.header, now_ns, n};
  if (held_ == 0) {
    oldest_held_ns_ = now_ns;
  }
  ++held_;
}
// [/snippet:offer]

template <typename Deliver>
void SequenceTracker::deliver_ready(Deliver& deliver) {
  for (;;) {
    Slot& s = slots_[index_of(next_)];
    if (!s.used || s.header.sequence != next_) {
      return;
    }
    deliver(s.header, std::span<const std::byte>(storage(index_of(next_)).first(s.bytes)));
    ++stats_.delivered;
    stats_.words += s.header.word_count;
    s.used = false;
    --held_;
    ++next_;
    if (held_ > 0) {
      // The next gap's clock starts from the earliest packet still held.
      oldest_held_ns_ = std::numeric_limits<std::int64_t>::max();
      for (const Slot& o : slots_) {
        if (o.used) {
          oldest_held_ns_ = std::min(oldest_held_ns_, o.arrived_ns);
        }
      }
    }
  }
}

template <typename Deliver>
void SequenceTracker::skip_gap(Deliver& deliver) {
  ++stats_.lost;
  ++next_;
  deliver_ready(deliver);
}

template <typename Deliver>
void SequenceTracker::expire(std::int64_t now_ns, Deliver deliver) {
  while (held_ > 0 && now_ns - oldest_held_ns_ >= cfg_.max_hold_ns) {
    skip_gap(deliver);
  }
}

template <typename Deliver>
void SequenceTracker::flush(Deliver deliver) {
  while (held_ > 0) {
    skip_gap(deliver);
  }
}

}  // namespace minidaq::readout
