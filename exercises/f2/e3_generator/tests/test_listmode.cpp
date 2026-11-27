#include <gtest/gtest.h>

#include <cstring>
#include <stdexcept>
#include <vector>

#include "listmode.hpp"

using ex::Single;

namespace {
std::vector<std::byte> encode(const std::vector<Single>& singles) {
  std::vector<std::byte> out(singles.size() * ex::record_size);
  std::memcpy(out.data(), singles.data(), out.size());
  return out;
}
std::vector<Single> ramp(std::size_t n) {
  std::vector<Single> s(n);
  for (std::size_t i = 0; i < n; ++i) {
    s[i] = {static_cast<std::int64_t>(i) * 1000, static_cast<std::uint32_t>(i % 64),
            static_cast<float>(400 + (i * 37) % 250)};
  }
  return s;
}
}  // namespace

TEST(Generator, YieldsEveryRecordInOrder) {
  const auto in = ramp(100);
  const auto bytes = encode(in);
  std::size_t decoded = 0;
  std::vector<Single> out;
  for (const Single& s : ex::singles_in(bytes, decoded)) out.push_back(s);
  EXPECT_EQ(out, in);
  EXPECT_EQ(decoded, 100U);
}

TEST(Generator, IsLazy) {
  const auto bytes = encode(ramp(1000));
  std::size_t decoded = 0;
  auto gen = ex::singles_in(bytes, decoded);
  EXPECT_EQ(decoded, 0U) << "nothing runs before the first request";
  int taken = 0;
  for (const Single& s : gen) {
    (void)s;
    if (++taken == 3) break;
  }
  EXPECT_EQ(decoded, 3U) << "a caller who takes three singles decodes three records";
}

TEST(Generator, IgnoresATruncatedTail) {
  auto bytes = encode(ramp(5));
  bytes.resize(bytes.size() + 7);  // part of a sixth record
  std::size_t decoded = 0;
  std::size_t n = 0;
  for (const Single& s : ex::singles_in(bytes, decoded)) {
    (void)s;
    ++n;
  }
  EXPECT_EQ(n, 5U);
}

TEST(Generator, ComposesLazily) {
  const auto bytes = encode(ramp(1000));
  std::size_t decoded = 0;
  int taken = 0;
  for (const Single& s : ex::in_window(ex::singles_in(bytes, decoded), 435.0F, 585.0F)) {
    EXPECT_GE(s.energy_kev, 435.0F);
    EXPECT_LE(s.energy_kev, 585.0F);
    if (++taken == 2) break;
  }
  EXPECT_EQ(taken, 2);
  EXPECT_LT(decoded, 20U) << "the filter pulls only as many records as it needs";
}

TEST(Generator, ExceptionReachesTheCaller) {
  auto in = ramp(10);
  in[4].time_ps = -1;
  const auto bytes = encode(in);
  std::size_t decoded = 0;
  std::size_t n = 0;
  EXPECT_THROW(
      {
        for (const Single& s : ex::singles_in(bytes, decoded)) {
          (void)s;
          ++n;
        }
      },
      std::runtime_error);
  EXPECT_EQ(n, 4U) << "the four good singles before the bad record were delivered";
}
