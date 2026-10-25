// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <vector>

#include "packet.hpp"

using namespace ex72;

namespace {
std::vector<std::byte> sample() {
  const std::array<std::uint64_t, 3> w{1, 2, 0xFFFF'FFFF'FFFF'FFFF};
  return encode_packet(7, 42, w);
}
void poke8(std::vector<std::byte>& p, std::size_t at, std::uint8_t v) { p[at] = std::byte{v}; }
void poke16(std::vector<std::byte>& p, std::size_t at, std::uint16_t v) { std::memcpy(p.data() + at, &v, 2); }
}  // namespace

TEST(Packet, RoundTrip) {
  const auto p = sample();
  ASSERT_EQ(p.size(), 16U + 3 * 8);
  const auto info = parse_packet(p);
  ASSERT_TRUE(info) << info.error();
  EXPECT_EQ(info->board, 7);
  EXPECT_EQ(info->sequence, 42U);
  ASSERT_EQ(info->count, 3U);
  std::array<std::uint64_t, 3> w{};
  EXPECT_EQ(read_words(p, *info, w), 3U);
  EXPECT_EQ(w[2], 0xFFFF'FFFF'FFFF'FFFFULL);
}

TEST(Packet, TrailingBytesAndHeaderExtensionsAreAllowed) {
  auto p = sample();
  p.resize(p.size() + 5);  // padding after the words: ignored
  EXPECT_TRUE(parse_packet(p));
  // A 3-word header: one extension word the parser skips.
  auto q = sample();
  q.insert(q.begin() + 16, 8, std::byte{0xAB});
  poke8(q, 5, 3);
  const auto info = parse_packet(q);
  ASSERT_TRUE(info) << info.error();
  EXPECT_EQ(info->payload_offset, 24U);
  std::array<std::uint64_t, 3> w{};
  EXPECT_EQ(read_words(q, *info, w), 3U);
  EXPECT_EQ(w[0], 1U);
}

TEST(Packet, RejectsEveryLieInTheHeader) {
  {
    auto p = sample();
    p.resize(15);
    EXPECT_FALSE(parse_packet(p)) << "shorter than a header";
  }
  {
    auto p = sample();
    p[0] = std::byte{0};
    EXPECT_FALSE(parse_packet(p)) << "magic";
  }
  {
    auto p = sample();
    poke8(p, 4, 2);
    EXPECT_FALSE(parse_packet(p)) << "version";
  }
  {
    auto p = sample();
    poke16(p, 6, 4);
    EXPECT_FALSE(parse_packet(p)) << "count one more than the payload holds";
  }
  {
    auto p = sample();
    poke16(p, 6, 0xFFFF);
    EXPECT_FALSE(parse_packet(p)) << "count far beyond the packet";
  }
  {
    auto p = sample();
    poke8(p, 5, 1);
    EXPECT_FALSE(parse_packet(p)) << "header_words below 2 overlaps the header";
  }
  {
    auto p = sample();
    poke8(p, 5, 0xFF);
    EXPECT_FALSE(parse_packet(p)) << "header longer than the packet";
  }
  {
    auto p = sample();
    poke8(p, 5, 5);  // 40-byte header in a 40-byte packet: no room for 3 words
    EXPECT_FALSE(parse_packet(p)) << "header plus words longer than the packet";
  }
  {
    auto p = sample();
    poke16(p, 10, 1);
    EXPECT_FALSE(parse_packet(p)) << "reserved must be zero";
  }
}

TEST(Packet, CrashInputsFoundByFuzzingAreRejected) {
  // Each file in tests/crashers was written by libFuzzer while fuzzing the
  // starter. Keeping them as tests means the bug cannot come back unnoticed.
  const auto dir = std::filesystem::path{MINIDAQ_EXERCISE_TESTS_DIR} / "crashers";
  int n = 0;
  for (const auto& entry : std::filesystem::directory_iterator{dir}) {
    std::ifstream in{entry.path(), std::ios::binary};
    const std::vector<char> raw{std::istreambuf_iterator<char>{in}, {}};
    const auto bytes = std::as_bytes(std::span{raw});
    EXPECT_FALSE(parse_packet(bytes)) << entry.path().filename();
    ++n;
  }
  EXPECT_GE(n, 1);
}
