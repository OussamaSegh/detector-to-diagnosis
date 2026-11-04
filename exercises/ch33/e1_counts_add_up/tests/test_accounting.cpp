// SPDX-License-Identifier: MIT
// Acceptance tests of Exercise 33.1.
#include <gtest/gtest.h>

#include <algorithm>
#include <cstdint>
#include <random>
#include <string>
#include <vector>

#include "accounting.hpp"
#include "minidaq/core/geometry.hpp"

using namespace minidaq;

namespace {

struct Sorted {
  SorterStats stats;
  std::vector<Coincidence> written;
};

// 200,000 singles at about 100 M singles/s (a mean gap of 10 ns, so many windows hold two or
// more), energies across and beyond the window, one in 500 put out of order.
Sorted sort_random(std::uint64_t seed) {
  std::mt19937_64 rng{seed};
  std::uniform_int_distribution<std::uint32_t> crystal(0, ScannerGeometry::num_crystals - 1);
  std::exponential_distribution<double> gap(1.0 / 10'000.0);
  std::uniform_real_distribution<float> energy(380.0F, 650.0F);
  std::uniform_int_distribution<int> one_in(0, 499);
  std::vector<Single> singles;
  std::int64_t t = 1'000'000;
  for (int i = 0; i < 200'000; ++i) {
    t += static_cast<std::int64_t>(gap(rng));
    const std::int64_t when = one_in(rng) == 0 ? t - 50'000'000 : t;
    singles.push_back(Single{Picoseconds{when}, CrystalId{crystal(rng)}, KeV{energy(rng)}});
  }
  CoincidenceSorter sorter{SorterConfig{}};
  Sorted run;
  std::uniform_int_distribution<std::size_t> chunk(1, 5000);
  for (std::size_t i = 0; i < singles.size();) {
    const std::size_t n = std::min(chunk(rng), singles.size() - i);
    sorter.push(std::span{singles}.subspan(i, n), run.written);
    i += n;
  }
  sorter.flush(run.written);
  run.stats = sorter.stats();
  return run;
}

bool names(const std::vector<std::string>& errors, const std::string& name) {
  return std::ranges::find(errors, name) != errors.end();
}

}  // namespace

TEST(Accounting, TheSortersOwnCountersAddUp) {
  for (std::uint64_t seed = 1; seed <= 3; ++seed) {
    const Sorted run = sort_random(seed);
    ASSERT_GT(run.stats.prompts, 1000U);
    ASSERT_GT(run.stats.multiple_windows, 100U);
    ASSERT_GT(run.stats.out_of_order, 100U);
    ASSERT_GT(run.stats.delayed, 10U);
    EXPECT_EQ(ex33::accounting_errors(run.stats, run.written), std::vector<std::string>{});
  }
}

TEST(Accounting, EveryCounterOffByOneFailsTheEquationThatHoldsIt) {
  const Sorted run = sort_random(4);
  struct Counter {
    std::uint64_t SorterStats::*field;
    const char* name;
    const char* equation;
  };
  const Counter counters[] = {
      {&SorterStats::singles_in, "singles_in", "singles"},
      {&SorterStats::energy_rejected, "energy_rejected", "singles"},
      {&SorterStats::out_of_order, "out_of_order", "singles"},
      {&SorterStats::singles_alone, "singles_alone", "singles"},
      {&SorterStats::pair_windows, "pair_windows", "pair windows"},
      {&SorterStats::singles_in_multiples, "singles_in_multiples", "singles"},
      {&SorterStats::geometry_rejected, "geometry_rejected", "pair windows"},
      {&SorterStats::prompts, "prompts", "prompts written"},
      {&SorterStats::prompts_from_multiples, "prompts_from_multiples", "multiples"},
      {&SorterStats::delayed, "delayed", "delayed written"},
  };
  for (const auto& c : counters) {
    for (const int delta : {+1, -1}) {
      SorterStats s = run.stats;
      s.*c.field += static_cast<std::uint64_t>(delta);  // -1 wraps 0 to the largest value
      const auto errors = ex33::accounting_errors(s, run.written);
      EXPECT_TRUE(names(errors, c.equation)) << c.name << (delta > 0 ? " + 1" : " - 1");
    }
  }
}

TEST(Accounting, ACoincidenceLostOnTheWayToTheFileIsSeen) {
  Sorted run = sort_random(5);
  const auto prompt = std::ranges::find(run.written, CoincidenceKind::prompt, &Coincidence::kind);
  const auto delayed = std::ranges::find(run.written, CoincidenceKind::delayed, &Coincidence::kind);
  ASSERT_NE(prompt, run.written.end());
  ASSERT_NE(delayed, run.written.end());
  std::vector<Coincidence> less_one_prompt = run.written;
  less_one_prompt.erase(less_one_prompt.begin() + (prompt - run.written.begin()));
  EXPECT_EQ(ex33::accounting_errors(run.stats, less_one_prompt),
            std::vector<std::string>{"prompts written"});
  std::vector<Coincidence> less_one_delayed = run.written;
  less_one_delayed.erase(less_one_delayed.begin() + (delayed - run.written.begin()));
  EXPECT_EQ(ex33::accounting_errors(run.stats, less_one_delayed),
            std::vector<std::string>{"delayed written"});
}

TEST(Accounting, AMultipleWithFewerThanThreeSinglesIsImpossible) {
  SorterStats s;
  s.singles_in = 2;
  s.singles_in_multiples = 2;
  s.multiple_windows = 1;
  EXPECT_EQ(ex33::accounting_errors(s, {}), std::vector<std::string>{"multiples"});
}
