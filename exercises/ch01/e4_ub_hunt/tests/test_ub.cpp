#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "ub_snippet.hpp"

TEST(UbHunt, TotalDurationOfLongRun) {
  // 3 frames of 2^62 ps each: the sum does not fit in int64.
  const std::vector<std::int64_t> frames(3, std::int64_t{1} << 62);
  EXPECT_EQ(ex::total_duration_saturating(frames), std::numeric_limits<std::int64_t>::max());
}

TEST(UbHunt, EnergyHistogramTopBin) {
  std::array<std::uint32_t, 1024> hist{};
  ex::fill_energy_histogram(hist, {0.0F, 511.0F, 1023.9F, 1024.0F, 1500.0F});
  EXPECT_EQ(hist[0], 1U);
  EXPECT_EQ(hist[511], 1U);
  EXPECT_EQ(hist[1023], 3U);  // values at or above the range go to the overflow (top) bin
}

TEST(UbHunt, CrystalLabel) {
  std::vector<std::string> names = {"A0", "A1"};
  EXPECT_EQ(ex::label_and_extend(names, 100), "A0");
  EXPECT_EQ(names.size(), 102U);
}

TEST(UbHunt, ReadWordFromUnalignedBuffer) {
  std::array<std::byte, 16> buf{};
  const std::uint64_t w = 0x1122334455667788ULL;
  std::memcpy(buf.data() + 3, &w, 8);
  EXPECT_EQ(ex::read_word(buf.data() + 3), w);
}

TEST(UbHunt, ChannelMask) {
  EXPECT_EQ(ex::channel_mask(0), 1ULL);
  EXPECT_EQ(ex::channel_mask(40), 1ULL << 40);
  EXPECT_EQ(ex::channel_mask(63), 1ULL << 63);
}
