#include <gtest/gtest.h>

#include <numeric>
#include <stdexcept>
#include <vector>
#include <version>

#if defined(__cpp_lib_mdspan)
#include <mdspan>
#endif

#include "sinogram_view.hpp"

using ex::SinogramView;

TEST(SinogramView, Extents) {
  std::vector<float> data(12 * 5);
  SinogramView<float> v{data, 12, 5};
  EXPECT_EQ(v.angles(), 12U);
  EXPECT_EQ(v.bins(), 5U);
  EXPECT_EQ(v.size(), 60U);
}

TEST(SinogramView, RowMajorLayout) {
  std::vector<float> data(4 * 3);
  std::iota(data.begin(), data.end(), 0.0F);
  SinogramView<float> v{data, 4, 3};
  EXPECT_EQ((v[0, 0]), 0.0F);
  EXPECT_EQ((v[0, 2]), 2.0F);
  EXPECT_EQ((v[1, 0]), 3.0F);  // the next angle starts after `bins` values
  EXPECT_EQ((v[3, 2]), 11.0F);
}

TEST(SinogramView, WritesGoToTheUnderlyingBuffer) {
  std::vector<float> data(4 * 3, 0.0F);
  SinogramView<float> v{data, 4, 3};
  v[2, 1] += 7.0F;
  EXPECT_EQ(data[2 * 3 + 1], 7.0F);
}

TEST(SinogramView, RowIsASpanOverOneAngle) {
  std::vector<float> data(4 * 3);
  std::iota(data.begin(), data.end(), 0.0F);
  SinogramView<float> v{data, 4, 3};
  const std::span<float> r = v.row(2);
  ASSERT_EQ(r.size(), 3U);
  EXPECT_EQ(r[0], 6.0F);
  EXPECT_EQ(r.data(), data.data() + 6);
}

TEST(SinogramView, AtChecksBounds) {
  std::vector<float> data(4 * 3);
  SinogramView<float> v{data, 4, 3};
  EXPECT_NO_THROW((void)v.at(3, 2));
  EXPECT_THROW((void)v.at(4, 0), std::out_of_range);
  EXPECT_THROW((void)v.at(0, 3), std::out_of_range);
}

TEST(SinogramView, RejectsABufferOfTheWrongSize) {
  std::vector<float> data(10);
  EXPECT_THROW((SinogramView<float>{data, 4, 3}), std::invalid_argument);
}

TEST(SinogramView, ConstViewOfConstData) {
  const std::vector<float> data(6, 1.5F);
  SinogramView<const float> v{data, 2, 3};
  EXPECT_EQ((v[1, 2]), 1.5F);
}

#if defined(__cpp_lib_mdspan)
TEST(SinogramView, AgreesWithStdMdspan) {
  std::vector<float> data(6 * 4);
  std::iota(data.begin(), data.end(), 0.0F);
  SinogramView<float> v{data, 6, 4};
  std::mdspan m{data.data(), 6, 4};
  for (std::size_t a = 0; a < 6; ++a)
    for (std::size_t b = 0; b < 4; ++b) EXPECT_EQ((v[a, b]), (m[a, b]));
}
#endif
