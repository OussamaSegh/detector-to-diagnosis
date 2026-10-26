// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 25.3: every operation is cut by a power failure after each of its
// writes in turn; after the restart and repair(), the system must start, run a version that was
// checked, and let the operation be done again.
#include <gtest/gtest.h>

#include <functional>
#include <string>

#include "ab_slots.hpp"

using namespace ab;

namespace {

// What a system that can start looks like (the postcondition of repair()).
void expect_startable(const Disk& d, const std::string& when) {
  SCOPED_TRACE(when);
  ASSERT_EQ(d.current.has_value(), d.state.has_value()) << "current is set iff state is";
  if (!d.state) {
    return;
  }
  const std::size_t cur = *d.current;
  EXPECT_TRUE(d.slots.at(cur).checked) << "the running slot was checked";
  EXPECT_TRUE(cur == d.state->good || d.state->trial == cur) << "current is good or the trial";
  if (d.state->trial) {
    EXPECT_EQ(*d.state->trial, cur) << "a trial is the current slot";
    EXPECT_EQ(d.slots.at(cur).version, d.state->trial_version);
  }
  EXPECT_EQ(d.slots.at(d.state->good).version, d.state->good_version);
  EXPECT_TRUE(d.slots.at(d.state->good).checked);
}

// Runs `op` on `start` with the power cut after 0, 1, 2, ... writes, until it completes without a
// cut; after each cut, restarts with repair() and hands the repaired disk to `check`.
int cut_everywhere(const Disk& start, const std::function<void(Machine&)>& op,
                   const std::function<void(Machine&, int)>& check) {
  for (int n = 0;; ++n) {
    Machine m{start, n};
    try {
      op(m);
    } catch (const PowerCut&) {
      EXPECT_EQ(m.unsafe_moments(), 0) << "cut after " << n << " writes";
      Machine restarted{m.disk()};
      (void)repair(restarted);
      EXPECT_EQ(restarted.unsafe_moments(), 0);
      expect_startable(restarted.disk(), "after a cut after " + std::to_string(n) + " writes");
      check(restarted, n);
      continue;
    }
    EXPECT_EQ(m.unsafe_moments(), 0);
    expect_startable(m.disk(), "without a cut");
    check(m, n);  // the operation's result, which doing it again must not change
    return n;  // the number of cuts tried, which is the number of writes the operation makes
  }
}

Disk running(const std::string& good) {
  Disk d;
  d.slots[0] = Slot{good, true};
  d.slots[1] = Slot{"0.9.0", true};  // what was there before: a slot is never empty for long
  d.current = 0;
  d.state = State{0, good, std::nullopt, ""};
  return d;
}

Disk on_trial() {
  Disk d = running("1.0.0");
  d.slots[1] = Slot{"1.1.0", true};
  d.current = 1;
  d.state->trial = 1;
  d.state->trial_version = "1.1.0";
  return d;
}

}  // namespace

TEST(AbSlots, TheFirstInstallationSurvivesACutAfterAnyWrite) {
  const int writes = cut_everywhere(
      Disk{}, [](Machine& m) { install(m, "1.0.0"); },
      [](Machine& r, int) {
        if (!r.disk().state) {
          install(r, "1.0.0");  // done again from the start
        }
        ASSERT_TRUE(r.disk().current.has_value());
        EXPECT_EQ(r.disk().slots.at(*r.disk().current).version, "1.0.0");
        EXPECT_FALSE(r.disk().state->trial.has_value())
            << "the first installation is confirmed at once";
      });
  EXPECT_GE(writes, 3);
}

TEST(AbSlots, AnUpdateSurvivesACutAfterAnyWrite) {
  cut_everywhere(
      running("1.0.0"), [](Machine& m) { install(m, "1.1.0"); },
      [](Machine& r, int) {
        const Disk& d = r.disk();
        const std::string runs = d.slots.at(*d.current).version;
        EXPECT_TRUE(runs == "1.0.0" || runs == "1.1.0") << runs;
        EXPECT_EQ(d.state->good_version, "1.0.0") << "an update is never confirmed alone";
        if (!d.state->trial) {
          EXPECT_EQ(runs, "1.0.0");
          install(r, "1.1.0");
        }
        EXPECT_EQ(r.disk().slots.at(*r.disk().current).version, "1.1.0");
        EXPECT_EQ(r.disk().state->trial_version, "1.1.0");
      });
}

TEST(AbSlots, ARollbackSurvivesACutAfterAnyWrite) {
  cut_everywhere(on_trial(), rollback, [](Machine& r, int) {
    EXPECT_EQ(r.disk().state->good_version, "1.0.0") << "the trial never becomes good by accident";
    rollback(r);
    EXPECT_EQ(*r.disk().current, 0U);
    EXPECT_FALSE(r.disk().state->trial.has_value());
  });
}

TEST(AbSlots, AConfirmationSurvivesACutAfterAnyWrite) {
  cut_everywhere(on_trial(), confirm, [](Machine& r, int) {
    confirm(r);
    EXPECT_EQ(r.disk().state->good, 1U);
    EXPECT_EQ(r.disk().state->good_version, "1.1.0");
    EXPECT_EQ(*r.disk().current, 1U);
  });
}

TEST(AbSlots, NothingToDoWritesNothing) {
  for (const auto& op :
       {std::function<void(Machine&)>{confirm}, std::function<void(Machine&)>{rollback}}) {
    Machine m{running("1.0.0")};
    op(m);
    EXPECT_EQ(m.writes(), 0);
  }
  for (const Disk& d : {Disk{}, running("1.0.0"), on_trial()}) {
    Machine m{d};
    EXPECT_TRUE(repair(m).empty()) << "a consistent disk needs no repair";
    EXPECT_EQ(m.writes(), 0);
  }
}

TEST(AbSlots, AnUpdateThenARollbackRunsTheOldVersionAgain) {
  Machine m{running("1.0.0")};
  install(m, "1.1.0");
  EXPECT_EQ(m.disk().slots.at(*m.disk().current).version, "1.1.0");
  rollback(m);
  EXPECT_EQ(m.disk().slots.at(*m.disk().current).version, "1.0.0");
  install(m, "1.1.1");
  confirm(m);
  EXPECT_EQ(m.disk().state->good_version, "1.1.1");
  install(m, "1.2.0");
  EXPECT_EQ(*m.disk().current, 0U) << "the slots alternate";
  EXPECT_EQ(m.unsafe_moments(), 0);
}
