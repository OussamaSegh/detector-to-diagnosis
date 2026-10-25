// SPDX-License-Identifier: MIT
// MiniDAQ - the sending side of a readout link, simulated (Chapter 9): cut a
// time-ordered word stream into MDQ-R1 packets, and damage the packet stream
// the way a real network can (loss, reordering, duplication), reproducibly.
#pragma once

#include <cstddef>
#include <cstdint>
#include <random>
#include <span>
#include <vector>

#include "minidaq/format/readout_packet.hpp"

namespace minidaq::sim {

// One packet as it travels: the encoded datagram bytes.
struct Datagram {
  std::uint32_t sequence = 0;  // for tests and fault bookkeeping; the bytes are what counts
  std::vector<std::byte> bytes;
};

struct PacketizerConfig {
  std::uint16_t source = 0;
  std::uint32_t first_sequence = 0;  // tests start near 2^32 to cross the wrap
  std::size_t words_per_packet = readout::words_per_standard_mtu;
};

// [snippet:packetize]
// Cuts `words` into packets of words_per_packet words (the last one may be
// shorter); the last packet carries the end-of-stream flag if `end` is set.
// The sequence number continues across calls.
class Packetizer {
 public:
  explicit Packetizer(PacketizerConfig cfg);
  [[nodiscard]] std::vector<Datagram> packetize(std::span<const std::uint64_t> words, bool end);
  [[nodiscard]] std::uint32_t next_sequence() const noexcept { return next_; }

 private:
  PacketizerConfig cfg_;
  std::uint32_t next_;
};
// [/snippet:packetize]

// [snippet:faults]
struct LinkFaultConfig {
  double loss = 0.0;               // probability that a packet is dropped
  double reorder = 0.0;            // probability that a packet is delayed ...
  std::size_t max_displacement = 8;  // ... by 1 .. max_displacement positions
  double duplicate = 0.0;          // probability that a packet is sent twice
  std::uint64_t seed = 1;
};

struct LinkFaultCounts {
  std::uint64_t offered = 0;
  std::uint64_t lost = 0;
  std::uint64_t delayed = 0;
  std::uint64_t duplicated = 0;
  // Delayed and duplicated at once: the copy is sent on time and the original
  // late, so the late one is a duplicate, never a packet that came too late
  // (counted in both `delayed` and `duplicated`; MDQ-PR-018).
  std::uint64_t delayed_duplicated = 0;
};

// Applies the faults to a packet stream, in place. Each packet is first
// dropped with probability `loss`; a surviving packet is duplicated with
// probability `duplicate` (the copy follows it directly), and delayed with
// probability `reorder` by a uniform 1 .. max_displacement positions.
// Deterministic for a given seed and input.
class LinkFaults {
 public:
  explicit LinkFaults(LinkFaultConfig cfg);
  void apply(std::vector<Datagram>& packets);
  [[nodiscard]] const LinkFaultCounts& counts() const noexcept { return counts_; }

 private:
  LinkFaultConfig cfg_;
  std::mt19937_64 rng_;
  std::uniform_real_distribution<double> unit_{0.0, 1.0};
  LinkFaultCounts counts_;
};
// [/snippet:faults]

}  // namespace minidaq::sim
