// SPDX-License-Identifier: MIT
// Exercise 18.2, a solution: five properties of the fixed-window sorter in
// tests/subject.hpp, checked with MiniDAQ's property harness.
#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <map>
#include <span>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "subject.hpp"
#include "support/property.hpp"

namespace {

using minidaq::CrystalId;
using minidaq::KeV;
using minidaq::prop::Source;
using minidaq::prop::Verdict;

struct Case {
  ex::Config cfg;
  std::vector<ex::Single> singles;
  std::vector<std::size_t> cuts;  // batch boundaries
};

// The generator decides what the properties can find. It must produce the
// boundaries of the specification exactly: a partner exactly `window` later,
// energies exactly on the edges of the gate, equal times, and singles out of
// order. A uniformly random time or energy almost never hits them.
// [snippet:generator]
Case make_case(Source& src) {
  Case c;
  c.cfg.window = ex::Picoseconds{src.draw_signed(1, 5'000)};
  c.cfg.policy = src.coin() ? ex::Policy::take_winner : ex::Policy::kill_all;
  std::int64_t t = 0;
  for (std::size_t i = 0, n = src.draw(0, 40); i < n; ++i) {
    switch (src.pick(5)) {
      case 0: break;                                              // the same time
      case 1: t += c.cfg.window.count(); break;                   // exactly one window later
      case 2: t += src.draw_signed(0, c.cfg.window.count()); break;
      case 3: t += src.draw_signed(0, 5 * c.cfg.window.count()); break;
      default: t -= src.draw_signed(1, 3'000); break;             // out of order
    }
    double kev = 0.0;
    switch (src.pick(4)) {
      case 0: kev = c.cfg.energy_low_kev; break;
      case 1: kev = c.cfg.energy_high_kev; break;
      case 2: kev = src.uniform(435.0, 585.0); break;
      default: kev = src.uniform(0.0, 1'000.0); break;
    }
    c.singles.push_back(ex::Single{ex::Picoseconds{t}, CrystalId{static_cast<std::uint32_t>(i)},
                                   KeV{static_cast<float>(kev)}});
  }
  for (std::size_t k = src.draw(0, 4); k > 0 && !c.singles.empty(); --k) {
    c.cuts.push_back(src.draw(0, c.singles.size()));
  }
  std::sort(c.cuts.begin(), c.cuts.end());
  return c;
}
// [/snippet:generator]

std::string show(const Case& c) {
  std::ostringstream o;
  o << "window " << c.cfg.window.count() << ", " << (c.cfg.policy == ex::Policy::kill_all ? "kill_all" : "take_winner")
    << ", cuts";
  for (const auto x : c.cuts) {
    o << " " << x;
  }
  o << ";";
  for (const auto& s : c.singles) {
    o << " (" << s.time.count() << ", " << s.energy.count() << ")";
  }
  return o.str();
}

struct Result {
  std::vector<ex::Coincidence> out;
  ex::Stats stats;
};

Result sort(const Case& c, bool batches = true) {
  ex::Sorter s{c.cfg};
  Result r;
  std::size_t begin = 0;
  if (batches) {
    for (const auto cut : c.cuts) {
      s.push(std::span(c.singles).subspan(begin, cut - begin), r.out);
      begin = cut;
    }
  }
  s.push(std::span(c.singles).subspan(begin), r.out);
  s.flush(r.out);
  r.stats = s.stats();
  return r;
}

// A reference written from the specification, as plainly as possible: filter,
// then cut the whole stream into windows, then resolve each.
std::vector<ex::Coincidence> reference(const Case& c) {
  std::vector<ex::Single> s;
  for (const auto& x : c.singles) {
    const auto e = static_cast<double>(x.energy.count());
    if (e >= c.cfg.energy_low_kev && e <= c.cfg.energy_high_kev && (s.empty() || x.time >= s.back().time)) {
      s.push_back(x);
    }
  }
  std::vector<ex::Coincidence> out;
  for (std::size_t o = 0; o < s.size();) {
    std::size_t e = o;
    while (e < s.size() && s[e].time - s[o].time <= c.cfg.window) {
      ++e;
    }
    if (e - o == 2) {
      out.push_back({s[o], s[o + 1], ex::CoincidenceKind::prompt});
    } else if (e - o > 2 && c.cfg.policy == ex::Policy::take_winner) {
      std::size_t wi = o;
      std::size_t wj = o + 1;
      for (std::size_t i = o; i < e; ++i) {
        for (std::size_t j = i + 1; j < e; ++j) {
          if (s[i].energy.count() + s[j].energy.count() > s[wi].energy.count() + s[wj].energy.count()) {
            wi = i;
            wj = j;
          }
        }
      }
      out.push_back({s[wi], s[wj], ex::CoincidenceKind::prompt});
    }
    o = e;
  }
  return out;
}

TEST(SorterProperties, AgreesWithTheReference) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         const auto got = sort(c).out;
                         const auto want = reference(c);
                         return got == want ? "" : std::to_string(got.size()) + " prompts, the reference " +
                                                       std::to_string(want.size());
                       },
                       show);
}

TEST(SorterProperties, EveryPromptIsInsideTheWindow) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         for (const auto& k : sort(c).out) {
                           if (k.time_difference() < ex::Picoseconds{0} || k.time_difference() > c.cfg.window) {
                             return "a prompt " + std::to_string(k.time_difference().count()) + " ps apart";
                           }
                         }
                         return {};
                       },
                       show);
}

TEST(SorterProperties, NoSingleIsInTwoPrompts) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         std::map<std::uint32_t, int> uses;  // crystal ids are unique per case
                         for (const auto& k : sort(c).out) {
                           if (++uses[k.first.crystal.value()] > 1 || ++uses[k.second.crystal.value()] > 1) {
                             return "a single in two prompts";
                           }
                         }
                         return {};
                       },
                       show);
}

TEST(SorterProperties, BatchesDoNotMatter) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         const auto a = sort(c, true);
                         const auto b = sort(c, false);
                         if (a.out != b.out) {
                           return "different prompts";
                         }
                         return a.stats == b.stats ? "" : "different counters";
                       },
                       show);
}

TEST(SorterProperties, EverySingleIsAccountedFor) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         const auto st = sort(c).stats;
                         const auto sum = st.energy_rejected + st.out_of_order + st.singles_alone +
                                          (2 * st.pair_windows) + st.singles_in_multiples;
                         return st.singles_in == c.singles.size() && sum == st.singles_in
                                    ? ""
                                    : std::to_string(sum) + " of " + std::to_string(c.singles.size()) +
                                          " singles accounted for";
                       },
                       show);
}

}  // namespace
