// SPDX-License-Identifier: MIT
// Exercise 18.2: property tests of the fixed-window sorter in tests/subject.hpp.
// The generator and the one property here are a start; both need work.
#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <span>
#include <sstream>
#include <string>
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
};

// TODO: this generator draws times and energies uniformly. Which boundaries of
// the specification will it (almost) never produce?
Case make_case(Source& src) {
  Case c;
  c.cfg.window = ex::Picoseconds{src.draw_signed(1, 5'000)};
  c.cfg.policy = src.coin() ? ex::Policy::take_winner : ex::Policy::kill_all;
  std::int64_t t = 0;
  for (std::size_t i = 0, n = src.draw(0, 40); i < n; ++i) {
    t += src.draw_signed(0, 5 * c.cfg.window.count());
    const auto kev = static_cast<float>(src.uniform(0.0, 1'000.0));
    c.singles.push_back(ex::Single{ex::Picoseconds{t}, CrystalId{static_cast<std::uint32_t>(i)}, KeV{kev}});
  }
  return c;
}

std::string show(const Case& c) {
  std::ostringstream o;
  o << "window " << c.cfg.window.count() << ";";
  for (const auto& s : c.singles) {
    o << " (" << s.time.count() << ", " << s.energy.count() << ")";
  }
  return o.str();
}

std::vector<ex::Coincidence> sort(const Case& c) {
  ex::Sorter s{c.cfg};
  std::vector<ex::Coincidence> out;
  s.push(c.singles, out);
  s.flush(out);
  return out;
}

TEST(SorterProperties, NoPromptIsWiderThanTheWindow) {
  minidaq::prop::check(make_case,
                       [](const Case& c) -> Verdict {
                         for (const auto& k : sort(c)) {
                           if (k.time_difference() > c.cfg.window) {
                             return "a prompt " + std::to_string(k.time_difference().count()) + " ps apart";
                           }
                         }
                         return {};
                       },
                       show);
}

// TODO: more properties. Which of the specification's promises can a property
// check without knowing the answer? And for the rest: what answer could you
// compute another, simpler way?

}  // namespace
