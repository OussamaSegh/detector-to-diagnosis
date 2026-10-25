// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

#include "baseline_sorter.hpp"
#include "fast_sorter.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/sim/detector_simulator.hpp"

#if defined(__SANITIZE_ADDRESS__) || defined(__SANITIZE_THREAD__)
#define EX_SANITIZED 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer) || __has_feature(thread_sanitizer)
#define EX_SANITIZED 1
#endif
#endif

using namespace minidaq;

namespace {

const std::vector<Single>& stream() {
  static const std::vector<Single> v = [] {
    sim::SimulatorConfig c;
    c.activity_bq = 20e6;
    c.source = {sim::SourceShape::Kind::cylinder, {0.0, 0.0, 0.0}, 80.0, 100.0};
    c.phantom = {90.0, 180.0};
    c.seed = 14;
    sim::DetectorSimulator d{c};
    std::vector<Single> s;
    for (const auto& t : d.generate_until(Picoseconds{20'000'000'000})) {  // 20 ms
      s.push_back(t.single);
    }
    // Singles with equal times in crystal order, as MiniDAQ's sorter takes them (SRS-SRT-013).
    std::stable_sort(s.begin(), s.end(), [](const Single& a, const Single& b) {
      return a.time != b.time ? a.time < b.time : a.crystal < b.crystal;
    });
    return s;
  }();
  return v;
}

template <typename Sorter>
std::vector<Coincidence> run(Sorter& s, std::span<const Single> in, std::uint64_t chunk_seed) {
  std::vector<Coincidence> out;
  std::mt19937_64 rng{chunk_seed};
  std::size_t i = 0;
  while (i < in.size()) {
    const std::size_t n = std::min<std::size_t>(in.size() - i, rng() % 5000);
    s.push(in.subspan(i, n), out);
    i += n;
  }
  s.flush(out);
  return out;
}

std::vector<SorterConfig> configs() {
  std::vector<SorterConfig> v;
  for (auto p : {MultiplesPolicy::kill_all, MultiplesPolicy::take_all_goods, MultiplesPolicy::take_winner_of_goods,
                 MultiplesPolicy::keep_if_only_one_good}) {
    for (bool delayed : {false, true}) {
      SorterConfig c;
      c.multiples = p;
      c.delay = delayed ? Picoseconds{100'000} : Picoseconds{0};
      c.fov_radius_mm = 120.0;
      v.push_back(c);
    }
  }
  return v;
}

}  // namespace

TEST(FastSorter, FindsExactlyWhatMiniDaqFinds) {
  for (const auto& c : configs()) {
    CoincidenceSorter lib{c};
    const auto want = run(lib, stream(), 1);
    ex104::FastSorter fast{c};
    EXPECT_EQ(run(fast, stream(), 2), want) << to_string(c.multiples) << ", delay " << c.delay.count();
  }
}

TEST(FastSorter, TheBaselineIsCorrectToo) {
  // The starter is this baseline: correct, so only the speed test fails.
  for (const auto& c : configs()) {
    CoincidenceSorter lib{c};
    const auto want = run(lib, stream(), 1);
    ex104::BaselineSorter slow{c};
    EXPECT_EQ(run(slow, stream(), 3), want) << to_string(c.multiples) << ", delay " << c.delay.count();
  }
}

TEST(FastSorter, FastEnough) {
#if !defined(NDEBUG) || defined(EX_SANITIZED)
  GTEST_SKIP() << "speed is only checked in release builds without sanitizers";
#else
  SorterConfig c;
  c.multiples = MultiplesPolicy::take_winner_of_goods;
  c.fov_radius_mm = 120.0;
  const auto rate = [&](auto make) {
    auto s = make();
    std::vector<Coincidence> out;
    out.reserve(stream().size() / 4);
    const auto t0 = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < stream().size(); i += 4096) {
      s->push(std::span{stream()}.subspan(i, std::min<std::size_t>(4096, stream().size() - i)), out);
    }
    s->flush(out);
    const double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    return static_cast<double>(stream().size()) / sec;
  };
  // The work is in the singles that pass the energy gate: rejecting the
  // others costs a comparison. Rates below count only those.
  const auto passed = static_cast<double>(std::count_if(stream().begin(), stream().end(), [&](const Single& x) {
                        const auto e = static_cast<double>(x.energy.count());
                        return e >= c.energy_low_kev && e <= c.energy_high_kev;
                      })) /
                      static_cast<double>(stream().size());
  // Best of seven, with the two sorters interleaved: a slow spell of a shared
  // machine then hits both, and the ratio stays meaningful.
  double fast = 0.0;
  double slow = 0.0;
  for (int rep = 0; rep < 7; ++rep) {
    fast = std::max(fast, passed * rate([&] { return std::make_unique<ex104::FastSorter>(c); }));
    slow = std::max(slow, passed * rate([&] { return std::make_unique<ex104::BaselineSorter>(c); }));
  }
  RecordProperty("fast_singles_per_s", std::to_string(fast));
  RecordProperty("baseline_singles_per_s", std::to_string(slow));
  const char* env = std::getenv("EX_MIN_SPEEDUP");
  const double need = env != nullptr ? std::atof(env) : 2.0;
  EXPECT_GT(fast, need * slow) << "fast " << fast / 1e6 << " M singles/s, baseline " << slow / 1e6 << " M/s";
  const char* target = std::getenv("EX_MIN_SINGLES_PER_S");
  EXPECT_GT(fast, target != nullptr ? std::atof(target) : 30e6)
      << "the chapter's target: 30 M singles/s inside the energy window, on one core";
#endif
}
