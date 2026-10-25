// SPDX-License-Identifier: MIT
// Exercise 18.3, the starter: two tests of the sinogram histogrammer. Together they take well under
// half of the branches of minidaq/src/processing/sinogram.cpp both ways. Add tests, from the
// header's specification, until tests/check_coverage.py reports at least 90%, and account for
// each branch that is still open in review.json.
#include <gtest/gtest.h>

#include <cstdint>

#include "minidaq/core/geometry.hpp"
#include "minidaq/processing/sinogram.hpp"

using namespace minidaq;
using namespace minidaq::sino;

namespace {

Coincidence pair(std::uint32_t ring1, std::uint32_t t1, std::int64_t time1, std::uint32_t ring2, std::uint32_t t2,
                 std::int64_t time2) {
  return Coincidence{Single{Picoseconds{time1}, ScannerGeometry::make_crystal(ring1, t1), KeV{511.0F}},
                     Single{Picoseconds{time2}, ScannerGeometry::make_crystal(ring2, t2), KeV{511.0F}},
                     CoincidenceKind::prompt};
}

}  // namespace

TEST(SinogramBranches, APromptThroughTheCenterIsBinned) {
  Histogrammer h{SinogramConfig{}};
  h.add(pair(3, 10, 0, 3, 200, 100));
  EXPECT_EQ(h.stats().prompts, 1U);
}

TEST(SinogramBranches, TheDefaultConfigurationIsValid) {
  EXPECT_TRUE(validate(SinogramConfig{}).has_value());
}
