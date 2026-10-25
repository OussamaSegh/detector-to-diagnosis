// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <numeric>
#include <sstream>
#include <stdexcept>

#include "cyclictest_report.hpp"

namespace {

// Captured on the book's machine (Chapter 4, Section 4.5) with
//   cyclictest --policy=other -m -t2 -a1,2 -i200 -D3 -h200 -q
std::filesystem::path fixture() {
  return std::filesystem::path{MINIDAQ_EXERCISE_TESTS_DIR} / "fixtures" / "cyclictest_other_t2_h200.txt";
}

ex::CyclictestReport parse_text(const std::string& text) {
  std::istringstream in{text};
  return ex::parse_cyclictest(in);
}

}  // namespace

TEST(Cyclictest, ParsesRealTwoThreadOutput) {
  std::ifstream in{fixture()};
  ASSERT_TRUE(in) << fixture();
  const auto r = ex::parse_cyclictest(in);
  ASSERT_EQ(r.threads.size(), 2U);
  const auto& t0 = r.threads[0];
  const auto& t1 = r.threads[1];
  EXPECT_EQ(t0.bins.size(), 200U);
  EXPECT_EQ(t0.total, 14965U);
  EXPECT_EQ(t1.total, 14977U);
  EXPECT_EQ(t0.overflows, 9U);
  EXPECT_EQ(t1.overflows, 4U);
  EXPECT_EQ(t0.min_us, 10);
  EXPECT_EQ(t1.min_us, 12);
  EXPECT_EQ(t0.avg_us, 60);
  EXPECT_EQ(t0.max_us, 2485);
  EXPECT_EQ(t1.max_us, 1279);
  EXPECT_EQ(std::accumulate(t0.bins.begin(), t0.bins.end(), std::uint64_t{0}), t0.total);
}

TEST(Cyclictest, PercentilesCountOverflowsAsSamples) {
  std::ifstream in{fixture()};
  const auto r = ex::parse_cyclictest(in);
  ASSERT_EQ(r.threads.size(), 2U);
  const auto& t0 = r.threads[0];
  EXPECT_EQ(t0.samples(), 14974U);
  EXPECT_EQ(ex::percentile_us(t0, 50.0), 60);
  EXPECT_EQ(ex::percentile_us(t0, 99.0), 72);
  EXPECT_EQ(ex::percentile_us(t0, 99.9), 131);
  // Rank 14973 of 14974 is beyond the 14965 in-range samples.
  EXPECT_EQ(ex::percentile_us(t0, 99.99), std::nullopt);
  EXPECT_EQ(ex::percentile_us(r.threads[1], 99.0), 70);
  EXPECT_EQ(ex::percentile_us(r.threads[1], 99.9), 126);
}

TEST(Cyclictest, SmallHistogramEdgeCases) {
  const auto r = parse_text(
      "defaulting realtime priority to 2\n"
      "# /dev/cpu_dma_latency set to 0us\n"
      "# Histogram\n"
      "000000 000000\n"
      "000001 000003\n"
      "000002 000001\n"
      "# Total: 000000004\n"
      "# Min Latencies: 00001\n"
      "# Avg Latencies: 00001\n"
      "# Max Latencies: 00002\n"
      "# Histogram Overflows: 00000\n");
  ASSERT_EQ(r.threads.size(), 1U);
  const auto& t = r.threads[0];
  EXPECT_EQ(ex::percentile_us(t, 0.0), 1);  // rank 1, the smallest sample
  EXPECT_EQ(ex::percentile_us(t, 75.0), 1);
  EXPECT_EQ(ex::percentile_us(t, 75.1), 2);
  EXPECT_EQ(ex::percentile_us(t, 100.0), 2);
  EXPECT_EQ(ex::percentile_us(ex::CyclictestThread{}, 50.0), std::nullopt);
}

TEST(Cyclictest, RejectsMalformedInput) {
  EXPECT_THROW((void)parse_text("# Total: 1\n"), std::runtime_error);  // no histogram
  EXPECT_THROW((void)parse_text("# Histogram\n000000 000001\n000002 000001\n# Total: 2\n"),
               std::runtime_error);  // gap: row 1 missing
  EXPECT_THROW((void)parse_text("# Histogram\n000000 000001\n000001 000001 000001\n# Total: 2\n"),
               std::runtime_error);  // column count changed
  EXPECT_THROW((void)parse_text("# Histogram\n000000 000001\n000001 000001\n# Total: 3\n"),
               std::runtime_error);  // Total disagrees with rows
  EXPECT_THROW((void)parse_text("# Histogram\n000000 000001\n# Total: 1 1\n"),
               std::runtime_error);  // two totals for one thread
  EXPECT_THROW((void)parse_text("# Histogram\n000000 000001\n"), std::runtime_error);  // no Total
}

TEST(Cyclictest, ErrorNamesTheLine) {
  try {
    (void)parse_text("# Histogram\n000000 000001\n000002 000001\n# Total: 2\n");
    FAIL() << "expected an exception";
  } catch (const std::runtime_error& e) {
    EXPECT_NE(std::string{e.what()}.find("line 3"), std::string::npos) << e.what();
  }
}
