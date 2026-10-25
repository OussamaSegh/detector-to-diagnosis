// SPDX-License-Identifier: MIT
// Replaying a recorded stream (Chapter 11): the words come back in a loop with
// shifted time stamps, the decoded stream stays in time order, and delivery
// follows the wall clock.
#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <thread>
#include <vector>

#include "minidaq/core/clock.hpp"
#include "minidaq/core/geometry.hpp"
#include "minidaq/format/packed_single.hpp"
#include "minidaq/sim/replay_source.hpp"

using namespace minidaq;
using namespace std::chrono_literals;

namespace {

std::vector<std::uint64_t> recording() {
  // Four singles over 3 us, the last one just past a counter wrap.
  const std::int64_t wrap = packed::wrap_period_ps;
  std::vector<std::uint64_t> w;
  for (const std::int64_t t : {wrap - 2'000'000, wrap - 1'000'000, wrap - 5, wrap + 1'000'000}) {
    w.push_back(packed::encode(Single{Picoseconds{t}, CrystalId{7}, KeV{511.0F}}));
  }
  return w;
}

}  // namespace

TEST(ReplaySource, LoopsWithShiftedTimesInOrder) {
  // REQ: SRS-SIM-020
  sim::ReplaySource src{recording(), 1e9};  // far faster than the test can ask
  std::vector<std::uint64_t> out(4 * 50);
  std::size_t n = src(out);  // starts the clock (and delivers nothing yet)
  std::this_thread::sleep_for(2ms);  // sleep: minimum (lets words become due)
  while (n < out.size()) {
    n += src(std::span{out}.subspan(n));
  }
  std::vector<Single> s(out.size());
  packed::StreamDecoder dec{ScannerGeometry::num_crystals};
  ASSERT_EQ(dec.decode(out, s), out.size());
  EXPECT_TRUE(std::is_sorted(s.begin(), s.end(), [](const Single& a, const Single& b) { return a.time < b.time; }));
  // A loop lasts the 3 us span plus the mean gap of 1 us.
  for (std::size_t i = 4; i < s.size(); ++i) {
    EXPECT_EQ((s[i].time - s[i - 4].time).count(), 4'000'000) << i;
    EXPECT_EQ(s[i].crystal, s[i % 4].crystal);
    EXPECT_EQ(s[i].energy, s[i % 4].energy);
  }
}

TEST(ReplaySource, RealTimeRateAndPacing) {
  // REQ: SRS-SIM-021
  sim::ReplaySource real{recording(), 0.0};
  EXPECT_DOUBLE_EQ(real.real_time_rate(), 4.0 / 4e-6) << "4 words per 4 us loop";
  EXPECT_DOUBLE_EQ(real.rate(), real.real_time_rate());
  constexpr double rate = 2e5;
  sim::ReplaySource src{recording(), rate, 512};
  std::vector<std::uint64_t> buf(4096);
  const std::int64_t t0 = monotonic_ns();
  (void)src(buf);
  while (monotonic_ns() - t0 < 100'000'000) {
    if (src(buf) == 0) {
      std::this_thread::sleep_for(100us);  // sleep: poll
    }
  }
  const double elapsed_s = static_cast<double>(monotonic_ns() - t0) * 1e-9;
  EXPECT_LE(static_cast<double>(src.delivered()), rate * elapsed_s + 1.0);
  // It does deliver once a word is due; how many words 0.1 s brings depends on
  // how often this thread runs, so no throughput is asserted (CAPA-0001).
  const std::uint64_t next = src.delivered();
  while (monotonic_ns() < src.due_ns(next + 1) + 1'000) {
    std::this_thread::sleep_for(100us);  // sleep: poll
  }
  EXPECT_GT(src(buf), 0U) << "a due word is delivered";
  EXPECT_THROW(sim::ReplaySource({1}, 1.0), std::invalid_argument);
}
