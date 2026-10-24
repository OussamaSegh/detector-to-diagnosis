#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <limits>
#include <random>

#include "word.hpp"

TEST(PackedWord, FieldsDoNotOverlap) {
  using ex::Fields;
  const std::uint64_t c = ex::pack(Fields{ex::kCrystalMax, 0, 0, 0});
  const std::uint64_t e = ex::pack(Fields{0, ex::kEnergyMax, 0, 0});
  const std::uint64_t co = ex::pack(Fields{0, 0, ex::kCoarseMax, 0});
  const std::uint64_t f = ex::pack(Fields{0, 0, 0, ex::kFineMax});
  EXPECT_EQ(c & e, 0U);
  EXPECT_EQ(c & co, 0U);
  EXPECT_EQ(c & f, 0U);
  EXPECT_EQ(e & co, 0U);
  EXPECT_EQ(e & f, 0U);
  EXPECT_EQ(co & f, 0U);
  EXPECT_EQ(c | e | co | f, std::numeric_limits<std::uint64_t>::max());
}

TEST(PackedWord, UnpackInvertsPack) {
  std::mt19937_64 rng{7};
  for (int i = 0; i < 100'000; ++i) {
    const ex::Fields f{static_cast<std::uint32_t>(rng() % (ex::kCrystalMax + 1ULL)),
                       static_cast<std::uint32_t>(rng() % (ex::kEnergyMax + 1ULL)), rng() % (ex::kCoarseMax + 1ULL),
                       static_cast<std::uint32_t>(rng() % (ex::kFineMax + 1ULL))};
    const ex::Fields g = ex::unpack(ex::pack(f));
    ASSERT_EQ(g.crystal, f.crystal);
    ASSERT_EQ(g.energy_code, f.energy_code);
    ASSERT_EQ(g.coarse, f.coarse);
    ASSERT_EQ(g.fine, f.fine);
  }
}

TEST(PackedWord, EncodeDecodeRoundTrip) {
  std::mt19937_64 rng{11};
  std::uniform_int_distribution<std::int64_t> t(0, ex::kWrapPeriodPs * 3);
  std::uniform_int_distribution<std::uint32_t> c(0, ex::kCrystalMax);
  std::uniform_real_distribution<float> e(0.0F, ex::kEnergyMaxKeV);
  for (int i = 0; i < 200'000; ++i) {
    const ex::Single s{t(rng), c(rng), e(rng)};
    const ex::Single d = ex::decode(ex::encode(s));
    ASSERT_EQ(d.crystal, s.crystal);
    ASSERT_LE(std::fabs(d.energy_kev - s.energy_kev), ex::kEnergyLsbKeV / 2.0F + 1e-4F);
    const std::int64_t wrapped = s.time_ps % ex::kWrapPeriodPs;
    ASSERT_GE(wrapped - d.time_ps, 0);
    ASSERT_LT(wrapped - d.time_ps, ex::kTimeLsbPs);
  }
}

TEST(PackedWord, LittleEndianBytes) {
  const std::array<std::byte, 8> b = ex::to_bytes(0x0102030405060708ULL);
  EXPECT_EQ(b[0], std::byte{0x08});
  EXPECT_EQ(b[7], std::byte{0x01});
  EXPECT_EQ(ex::from_bytes(b), 0x0102030405060708ULL);
}
