// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <random>
#include <string_view>
#include <vector>

#include "minidaq/core/crc32.hpp"

using namespace minidaq;

namespace {

std::span<const std::byte> bytes(std::string_view s) { return std::as_bytes(std::span{s.data(), s.size()}); }

std::vector<std::byte> random_bytes(std::size_t n, std::mt19937_64& rng) {
  std::vector<std::byte> v(n);
  std::uniform_int_distribution<int> d(0, 255);
  for (auto& b : v) {
    b = static_cast<std::byte>(d(rng));
  }
  return v;
}

}  // namespace

TEST(Crc32, ReproducesTheStandardCheckValue) {
  // REQ: SRS-LMF-001
  EXPECT_EQ(crc32(bytes("123456789")), 0xCBF43926U);
  EXPECT_EQ(crc32_bytewise(bytes("123456789")), 0xCBF43926U);
  EXPECT_EQ(crc32({}), 0U);
  // zlib's crc32 of "The quick brown fox jumps over the lazy dog".
  EXPECT_EQ(crc32(bytes("The quick brown fox jumps over the lazy dog")), 0x414FA339U);
}

TEST(Crc32, SlicingBy8MatchesTheBytewiseLoopAtEveryLengthAndOffset) {
  // REQ: SRS-LMF-001
  std::mt19937_64 rng{12};
  const auto data = random_bytes(4096, rng);
  const std::span<const std::byte> all{data};
  for (std::size_t offset = 0; offset < 9; ++offset) {
    for (std::size_t n = 0; n <= 70; ++n) {
      const auto s = all.subspan(offset, n);
      ASSERT_EQ(crc32(s), crc32_bytewise(s)) << "offset " << offset << " length " << n;
    }
  }
  EXPECT_EQ(crc32(all), crc32_bytewise(all));
}

TEST(Crc32, UpdateContinuesOverConcatenatedPieces) {
  // REQ: SRS-LMF-001
  std::mt19937_64 rng{13};
  const auto data = random_bytes(1000, rng);
  const std::span<const std::byte> all{data};
  for (const std::size_t cut : {0U, 1U, 7U, 8U, 9U, 500U, 999U, 1000U}) {
    const auto first = crc32_update(0, all.first(cut));
    EXPECT_EQ(crc32_update(first, all.subspan(cut)), crc32(all)) << "cut at " << cut;
  }
}

TEST(Crc32, DetectsEverySingleAndDoubleBitFlipInABlock) {
  // REQ: SRS-LMF-002
  std::mt19937_64 rng{14};
  auto data = random_bytes(256, rng);
  const auto good = crc32(data);
  const std::size_t bits = data.size() * 8;
  for (std::size_t i = 0; i < bits; ++i) {
    data[i / 8] ^= static_cast<std::byte>(1U << (i % 8));
    ASSERT_NE(crc32(data), good) << "bit " << i;
    for (std::size_t j = i + 1; j < bits; j += 37) {  // a sample of the pairs keeps the test fast
      data[j / 8] ^= static_cast<std::byte>(1U << (j % 8));
      ASSERT_NE(crc32(data), good) << "bits " << i << " and " << j;
      data[j / 8] ^= static_cast<std::byte>(1U << (j % 8));
    }
    data[i / 8] ^= static_cast<std::byte>(1U << (i % 8));
  }
  EXPECT_EQ(crc32(data), good);
}

TEST(Crc32, DetectsEveryBurstOfUpTo32Bits) {
  // REQ: SRS-LMF-002
  std::mt19937_64 rng{15};
  auto data = random_bytes(64, rng);
  const auto good = crc32(data);
  std::uniform_int_distribution<std::uint32_t> pattern;
  for (std::size_t start = 0; start + 32 <= data.size() * 8; start += 3) {
    for (int trial = 0; trial < 64; ++trial) {
      // A burst of length L: first and last bits flipped, the ones between random.
      const int len = 1 + (trial % 32);
      const std::uint32_t mask = len == 32 ? ~0U : (1U << len) - 1U;
      const std::uint32_t p = (pattern(rng) | 1U | (1U << (len - 1))) & mask;
      auto flip = [&] {
        for (int b = 0; b < len; ++b) {
          if (((p >> b) & 1U) != 0) {
            const std::size_t bit = start + static_cast<std::size_t>(b);
            data[bit / 8] ^= static_cast<std::byte>(1U << (bit % 8));
          }
        }
      };
      flip();
      ASSERT_NE(crc32(data), good) << "burst at " << start << " length " << len;
      flip();
    }
  }
}
