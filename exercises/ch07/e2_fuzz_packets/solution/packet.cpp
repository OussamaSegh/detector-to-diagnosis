// SPDX-License-Identifier: MIT
#include "packet.hpp"

#include <cstring>

#include "minidaq/core/bits.hpp"

namespace ex72 {
namespace {
template <typename T>
T load(std::span<const std::byte> p, std::size_t at) {
  T v{};
  std::memcpy(&v, p.data() + at, sizeof v);
  return minidaq::from_little_endian(v);
}
template <typename T>
void store(std::vector<std::byte>& p, std::size_t at, T v) {
  v = minidaq::to_little_endian(v);
  std::memcpy(p.data() + at, &v, sizeof v);
}
}  // namespace

minidaq::Expected<PacketInfo, std::string> parse_packet(std::span<const std::byte> packet) {
  if (packet.size() < min_header_bytes) {
    return minidaq::Unexpected{std::string{"shorter than a header"}};
  }
  if (load<std::uint32_t>(packet, 0) != packet_magic) {
    return minidaq::Unexpected{std::string{"bad magic"}};
  }
  if (load<std::uint8_t>(packet, 4) != 1) {
    return minidaq::Unexpected{std::string{"unsupported version"}};
  }
  // [snippet:checks]
  // Every length in the header is a claim; check each against the bytes that
  // actually arrived before anything is read at an offset derived from it.
  const std::size_t header_words = load<std::uint8_t>(packet, 5);
  if (header_words < min_header_bytes / 8) {
    return minidaq::Unexpected{std::string{"header shorter than 2 words"}};
  }
  if (header_words * 8 > packet.size()) {
    return minidaq::Unexpected{std::string{"header longer than the packet"}};
  }
  const std::size_t count = load<std::uint16_t>(packet, 6);
  // No overflow: count < 2^16 and header_words < 2^8, so both products are small.
  if (count * 8 > packet.size() - header_words * 8) {
    return minidaq::Unexpected{std::string{"count larger than the payload"}};
  }
  if (load<std::uint16_t>(packet, 10) != 0) {
    return minidaq::Unexpected{std::string{"reserved field not zero"}};
  }
  // [/snippet:checks]
  PacketInfo info;
  info.payload_offset = header_words * 8;
  info.count = count;
  info.board = load<std::uint16_t>(packet, 8);
  info.sequence = load<std::uint32_t>(packet, 12);
  return info;
}

std::size_t read_words(std::span<const std::byte> packet, const PacketInfo& info, std::span<std::uint64_t> out) {
  const std::size_t n = info.count < out.size() ? info.count : out.size();
  for (std::size_t i = 0; i < n; ++i) {
    out[i] = load<std::uint64_t>(packet, info.payload_offset + i * 8);
  }
  return n;
}

std::vector<std::byte> encode_packet(std::uint16_t board, std::uint32_t sequence, std::span<const std::uint64_t> words) {
  std::vector<std::byte> p(min_header_bytes + words.size() * 8);
  store<std::uint32_t>(p, 0, packet_magic);
  store<std::uint8_t>(p, 4, 1);
  store<std::uint8_t>(p, 5, 2);
  store<std::uint16_t>(p, 6, static_cast<std::uint16_t>(words.size()));
  store<std::uint16_t>(p, 8, board);
  store<std::uint32_t>(p, 12, sequence);
  for (std::size_t i = 0; i < words.size(); ++i) {
    store<std::uint64_t>(p, min_header_bytes + i * 8, words[i]);
  }
  return p;
}

}  // namespace ex72
