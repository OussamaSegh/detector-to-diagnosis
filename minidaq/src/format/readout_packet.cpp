// SPDX-License-Identifier: MIT
#include "minidaq/format/readout_packet.hpp"

#include <bit>
#include <stdexcept>

namespace minidaq::readout {

namespace {

// Little-endian field access on bytes, independent of the host's byte order
// and of alignment.
template <typename T>
T load_le(std::span<const std::byte> b, std::size_t at) noexcept {
  T v = 0;
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    v = static_cast<T>(v | (static_cast<T>(std::to_integer<std::uint8_t>(b[at + i])) << (8 * i)));
  }
  return v;
}

template <typename T>
void store_le(std::span<std::byte> b, std::size_t at, T v) noexcept {
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    b[at + i] = static_cast<std::byte>((v >> (8 * i)) & 0xFF);
  }
}

}  // namespace

std::string_view to_string(PacketError e) noexcept {
  switch (e) {
    case PacketError::too_short: return "too_short";
    case PacketError::bad_magic: return "bad_magic";
    case PacketError::bad_version: return "bad_version";
    case PacketError::bad_flags: return "bad_flags";
    case PacketError::bad_word_count: return "bad_word_count";
    case PacketError::bad_length: return "bad_length";
    case PacketError::bad_reserved: return "bad_reserved";
  }
  return "unknown";
}

std::size_t encode_packet(const PacketHeader& h, std::span<const std::uint64_t> words,
                          std::span<std::byte> out) noexcept {
  const std::size_t bytes = header_bytes + words.size() * word_bytes;
  if (words.empty() || words.size() > max_words || out.size() < bytes) {
    return 0;
  }
  std::copy(magic.begin(), magic.end(), out.begin());
  store_le<std::uint8_t>(out, 4, version);
  store_le<std::uint8_t>(out, 5, h.flags);
  store_le<std::uint16_t>(out, 6, h.source);
  store_le<std::uint32_t>(out, 8, h.sequence);
  store_le<std::uint16_t>(out, 12, static_cast<std::uint16_t>(words.size()));
  store_le<std::uint16_t>(out, 14, 0);
  for (std::size_t i = 0; i < words.size(); ++i) {
    store_le<std::uint64_t>(out, header_bytes + i * word_bytes, words[i]);
  }
  return bytes;
}

// [snippet:parse]
Expected<PacketView, PacketError> parse_packet(std::span<const std::byte> d) noexcept {
  if (d.size() < header_bytes) {
    return Unexpected{PacketError::too_short};
  }
  if (!std::equal(magic.begin(), magic.end(), d.begin())) {
    return Unexpected{PacketError::bad_magic};
  }
  if (load_le<std::uint8_t>(d, 4) != version) {
    return Unexpected{PacketError::bad_version};
  }
  PacketHeader h;
  h.flags = load_le<std::uint8_t>(d, 5);
  h.source = load_le<std::uint16_t>(d, 6);
  h.sequence = load_le<std::uint32_t>(d, 8);
  h.word_count = load_le<std::uint16_t>(d, 12);
  if ((h.flags & ~flag_end_of_stream) != 0) {
    return Unexpected{PacketError::bad_flags};
  }
  if (h.word_count == 0 || h.word_count > max_words) {
    return Unexpected{PacketError::bad_word_count};
  }
  if (d.size() != header_bytes + std::size_t{h.word_count} * word_bytes) {
    return Unexpected{PacketError::bad_length};
  }
  if (load_le<std::uint16_t>(d, 14) != 0) {
    return Unexpected{PacketError::bad_reserved};
  }
  return PacketView{h, d.subspan(header_bytes)};
}
// [/snippet:parse]

std::uint64_t payload_word(std::span<const std::byte> payload, std::size_t i) noexcept {
  return load_le<std::uint64_t>(payload, i * word_bytes);
}

namespace {
// The window must be a power of two: slots are indexed by sequence % window,
// and only a divisor of 2^32 keeps that mapping one-to-one across the wrap
// from 2^32 - 1 to 0. Checked before anything is allocated.
TrackerConfig checked(TrackerConfig cfg) {
  if (!std::has_single_bit(cfg.window_packets) || cfg.window_packets > 4096 || cfg.max_hold_ns < 0 ||
      cfg.max_gap_packets < cfg.window_packets || cfg.max_gap_packets > (std::uint32_t{1} << 30)) {
    throw std::invalid_argument(
        "SequenceTracker: window_packets must be a power of two <= 4096, max_hold_ns >= 0, "
        "max_gap_packets in [window_packets, 2^30]");
  }
  return cfg;
}
}  // namespace

SequenceTracker::SequenceTracker(TrackerConfig cfg)
    : cfg_{checked(cfg)}, slot_bytes_{max_words * word_bytes}, slots_(cfg_.window_packets),
      data_(cfg_.window_packets * max_words * word_bytes) {}

}  // namespace minidaq::readout
