#include <gtest/gtest.h>

#include <functional>
#include <span>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

#include "spectrum.hpp"

using ex::Spectrum;

namespace {
// Does `view` lie inside `owner`? Compares addresses only, never reads through `view`, so the
// test itself has no undefined behavior when the view dangles.
bool points_into(std::span<const int> view, std::span<const int> owner) {
  const std::less_equal<const int*> le;
  return le(owner.data(), view.data()) &&
         le(view.data() + view.size(), owner.data() + owner.size());
}
}  // namespace

TEST(Spectrum, PeakRegionViewsTheSpectrumItself) {
  const Spectrum s{"LSO", {1, 4, 9, 30, 12, 3}};
  const auto peak = s.peak_region(2, 5);
  ASSERT_EQ(peak.size(), 3U);
  ASSERT_TRUE(points_into(peak, s.storage())) << "the span points into a destroyed temporary";
  EXPECT_EQ(peak[0], 9);
  EXPECT_EQ(peak[1], 30);
  EXPECT_EQ(peak[2], 12);
}

TEST(Spectrum, PeakRegionChecksItsBounds) {
  const Spectrum s{"LSO", {1, 2, 3}};
  EXPECT_THROW((void)s.peak_region(2, 5), std::out_of_range);
  EXPECT_THROW((void)s.peak_region(2, 1), std::out_of_range);
  EXPECT_TRUE(s.peak_region(1, 1).empty());
}

TEST(Spectrum, LabelOwnsItsText) {
  // A label built from two pieces exists nowhere until label() builds it, so it must be
  // returned by value. A string_view of it would view a temporary that dies at the return.
  using Label = decltype(std::declval<const Spectrum&>().label());
  EXPECT_TRUE((std::is_same_v<Label, std::string>));
}

TEST(Spectrum, LabelText) {
  const Spectrum s{"BGO", {0}};
  if constexpr (std::is_same_v<decltype(s.label()), std::string>) {
    EXPECT_EQ(s.label(), "BGO spectrum");
  } else {
    GTEST_SKIP() << "label() returns a view of a temporary; reading it is undefined behavior";
  }
}
