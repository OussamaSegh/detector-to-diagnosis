// SPDX-License-Identifier: MIT
// Exercise 7.2: a readout packet parser, the first code that a network
// receiver (Chapter 9) runs on bytes from outside the PC.
//
// Packet layout, all fields little-endian:
//   offset 0   u32  magic 0x5141444D ("MDAQ" in memory)
//          4   u8   version (1)
//          5   u8   header_words: header length in 8-byte words, at least 2
//          6   u16  count: number of 64-bit single words after the header
//          8   u16  board
//         10   u16  reserved (0)
//         12   u32  sequence number
//   header_words * 8: count words of 8 bytes; trailing bytes after them are ignored.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

#include "minidaq/core/expected.hpp"

namespace ex72 {

inline constexpr std::uint32_t packet_magic = 0x5141444D;
inline constexpr std::size_t min_header_bytes = 16;

struct PacketInfo {
  std::uint16_t board = 0;
  std::uint32_t sequence = 0;
  std::size_t count = 0;           // single words in the packet
  std::size_t payload_offset = 0;  // where the first word starts
};

// Checks the header of `packet` against the packet's real size.
[[nodiscard]] minidaq::Expected<PacketInfo, std::string> parse_packet(std::span<const std::byte> packet);

// Copies the packet's words into `out` (at most out.size()); returns how many.
// `info` must come from parse_packet(packet).
std::size_t read_words(std::span<const std::byte> packet, const PacketInfo& info, std::span<std::uint64_t> out);

// Builds a packet with header_words = 2.
[[nodiscard]] std::vector<std::byte> encode_packet(std::uint16_t board, std::uint32_t sequence,
                                                   std::span<const std::uint64_t> words);

}  // namespace ex72
