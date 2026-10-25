// SPDX-License-Identifier: MIT
// MiniDAQ - property-based testing for the unit tests (Chapter 18, ADR 0015).
//
// A property is a statement that must hold for every input of a kind: "for any
// time-ordered stream, every prompt's time difference is within the window".
// prop::check() generates many inputs, and when one fails it shrinks it to a
// small input that still fails, which is the counterexample you debug.
//
// Generators draw from a Source, which records every choice as a 64-bit
// number. Shrinking works on that sequence of choices, not on the value: a
// shorter sequence, or one with smaller numbers, gives a simpler input for any
// generator, so no generator needs its own shrinking code (the approach of
// Hypothesis; RapidCheck shrinks values instead).
//
// Every run is reproducible. The seed is fixed per test (a hash of its name)
// unless MINIDAQ_PROP_SEED sets it, and MINIDAQ_PROP_CASES multiplies the
// number of cases, for a longer search before a release. A failure prints the
// seed and the shrunk choices; MINIDAQ_PROP_REPLAY="c1,c2,..." replays them.
#pragma once

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <functional>
#include <limits>
#include <random>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace minidaq::prop {

// [snippet:source]
class Source {
 public:
  // Random choices from `seed`.
  explicit Source(std::uint64_t seed) : rng_{seed} {}
  // Replays recorded choices; past their end every choice is 0, the simplest.
  explicit Source(std::vector<std::uint64_t> replay) : replay_{std::move(replay)}, replaying_{true} {}

  // A value in [lo, hi]. The choice recorded is the offset from lo, so a
  // smaller choice is always a value closer to lo, which is what lets the
  // shrinker search each choice by bisection.
  std::uint64_t draw(std::uint64_t lo, std::uint64_t hi) { return lo + next(hi - lo); }
  // [/snippet:source]
  std::int64_t draw_signed(std::int64_t lo, std::int64_t hi) {
    const auto span = static_cast<std::uint64_t>(hi) - static_cast<std::uint64_t>(lo);
    return static_cast<std::int64_t>(static_cast<std::uint64_t>(lo) + draw(0, span));
  }
  // True with probability about `p`; shrinks toward false.
  bool coin(double p = 0.5) {
    constexpr std::uint64_t steps = 1'000'000;
    return draw(0, steps - 1) >= static_cast<std::uint64_t>((1.0 - p) * steps);
  }
  // A double in [lo, hi), in 2^20 steps; shrinks toward lo.
  double uniform(double lo, double hi) {
    constexpr std::uint64_t steps = std::uint64_t{1} << 20;
    return lo + (hi - lo) * static_cast<double>(draw(0, steps - 1)) / static_cast<double>(steps);
  }
  // One of `n` options, shrinking toward the first.
  std::size_t pick(std::size_t n) { return static_cast<std::size_t>(draw(0, n - 1)); }

  [[nodiscard]] const std::vector<std::uint64_t>& choices() const noexcept { return made_; }

 private:
  // A choice in [0, max].
  std::uint64_t next(std::uint64_t max) {
    std::uint64_t c = 0;
    if (!replaying_) {
      c = rng_();
      if (max != std::numeric_limits<std::uint64_t>::max()) {
        c %= max + 1;  // the bias is below 2^-40 for the ranges used here
      }
    } else if (made_.size() < replay_.size()) {
      c = std::min(replay_[made_.size()], max);
    }
    made_.push_back(c);
    return c;
  }

  std::mt19937_64 rng_{0};
  std::vector<std::uint64_t> replay_;
  bool replaying_ = false;
  std::vector<std::uint64_t> made_;
};

struct Config {
  int cases = 200;         // inputs generated, times MINIDAQ_PROP_CASES
  int max_shrinks = 5000;  // property evaluations spent on shrinking
};

namespace detail {

inline std::uint64_t env_u64(const char* name, std::uint64_t fallback) {
  const char* v = std::getenv(name);  // NOLINT(concurrency-mt-unsafe): read before any test thread
  if (v == nullptr || *v == '\0') {
    return fallback;
  }
  return std::strtoull(v, nullptr, 0);
}

inline std::uint64_t name_seed() {
  const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
  std::uint64_t h = 1469598103934665603ULL;  // FNV-1a
  for (const std::string& part : {std::string{info->test_suite_name()}, std::string{info->name()}}) {
    for (const char ch : part) {
      h = (h ^ static_cast<unsigned char>(ch)) * 1099511628211ULL;
    }
  }
  return h;
}

inline std::vector<std::uint64_t> env_replay() {
  std::vector<std::uint64_t> out;
  const char* v = std::getenv("MINIDAQ_PROP_REPLAY");  // NOLINT(concurrency-mt-unsafe)
  if (v == nullptr) {
    return out;
  }
  std::stringstream ss{v};
  std::string item;
  while (std::getline(ss, item, ',')) {
    out.push_back(std::strtoull(item.c_str(), nullptr, 0));
  }
  return out;
}

// Shortlex order: a shorter sequence is simpler, then the smaller one.
inline bool simpler(const std::vector<std::uint64_t>& a, const std::vector<std::uint64_t>& b) {
  return a.size() != b.size() ? a.size() < b.size() : a < b;
}

}  // namespace detail

// The outcome of a property for one input: empty if it holds, else why not.
using Verdict = std::string;

// [snippet:check]
// Checks `property(gen(source))` for many sources. `gen` is
// T(Source&); `property` is Verdict(const T&); `describe` turns a T into text
// for the failure message.
template <class Gen, class Property, class Describe>
void check(Gen gen, Property property, Describe describe, Config cfg = {}) {
  const auto evaluate = [&](Source& src, std::string& shown) -> Verdict {
    try {
      const auto value = gen(src);
      Verdict v = property(value);
      if (!v.empty()) {
        shown = describe(value);
      }
      return v;
    } catch (const std::exception& e) {
      shown = "(the generator or the property threw)";
      return std::string{"threw: "} + e.what();
    }
  };
  const std::uint64_t seed = detail::env_u64("MINIDAQ_PROP_SEED", detail::name_seed());
  const auto cases = static_cast<std::uint64_t>(cfg.cases) * detail::env_u64("MINIDAQ_PROP_CASES", 1);

  std::vector<std::uint64_t> failing = detail::env_replay();
  Verdict why;
  std::string shown;
  std::uint64_t failed_case = 0;
  if (!failing.empty()) {
    Source src{failing};
    why = evaluate(src, shown);
  }
  for (std::uint64_t i = 0; failing.empty() && i < cases; ++i) {
    Source src{seed + i};
    why = evaluate(src, shown);
    if (!why.empty()) {
      failing = src.choices();
      failed_case = i;
    }
  }
  if (why.empty()) {
    return;
  }

  // Shrink: delete blocks of choices, then lower each choice, keeping any
  // change after which the property still fails.
  int budget = cfg.max_shrinks;
  int steps = 0;
  const auto attempt = [&](std::vector<std::uint64_t> candidate) {
    if (budget-- <= 0) {
      return false;
    }
    Source src{std::move(candidate)};
    std::string candidate_shown;
    Verdict v = evaluate(src, candidate_shown);
    if (v.empty()) {
      return false;
    }
    std::vector<std::uint64_t> used = src.choices();
    if (!detail::simpler(used, failing)) {
      return false;
    }
    failing = std::move(used);
    why = std::move(v);
    shown = std::move(candidate_shown);
    ++steps;
    return true;
  };
  for (bool progress = true; progress && budget > 0;) {
    progress = false;
    for (std::size_t block : {8U, 4U, 2U, 1U}) {
      for (std::size_t at = 0; at + block <= failing.size();) {
        auto c = failing;
        c.erase(c.begin() + static_cast<std::ptrdiff_t>(at), c.begin() + static_cast<std::ptrdiff_t>(at + block));
        if (attempt(std::move(c))) {
          progress = true;
        } else {
          ++at;
        }
      }
    }
    for (std::size_t at = 0; at < failing.size(); ++at) {
      // Binary search for the smallest choice at `at` that still fails.
      std::uint64_t lo = 0;
      std::uint64_t hi = failing[at];
      while (lo < hi && budget > 0) {
        const std::uint64_t mid = lo + ((hi - lo) / 2);
        auto c = failing;
        c[at] = mid;
        if (attempt(std::move(c))) {
          progress = true;
          hi = at < failing.size() ? failing[at] : 0;
        } else {
          lo = mid + 1;
        }
      }
    }
  }

  std::ostringstream msg;
  msg << "property failed: " << why << "\n  input: " << shown << "\n  found by case " << failed_case
      << " of seed " << seed << ", shrunk in " << steps << " steps\n  replay: MINIDAQ_PROP_REPLAY=\"";
  for (std::size_t i = 0; i < failing.size(); ++i) {
    msg << (i == 0 ? "" : ",") << failing[i];
  }
  msg << "\"";
  ADD_FAILURE() << msg.str();
}
// [/snippet:check]

}  // namespace minidaq::prop
