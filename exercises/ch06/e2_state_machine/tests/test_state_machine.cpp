// SPDX-License-Identifier: MIT
// Acceptance tests for Exercise 6.2.
#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <future>
#include <memory>
#include <mutex>
#include <random>
#include <set>
#include <thread>
#include <tuple>
#include <vector>

#include "state_machine.hpp"

using namespace std::chrono_literals;
using ex::Event;
using ex::State;

namespace {

// The specification, written independently of the solution's table.
const std::set<std::tuple<State, Event, State>> spec{
    {State::idle, Event::configure, State::configured},
    {State::configured, Event::configure, State::configured},
    {State::configured, Event::calibrate, State::calibrating},
    {State::calibrating, Event::drained, State::configured},
    {State::configured, Event::start, State::running},
    {State::configured, Event::reset, State::idle},
    {State::running, Event::stop, State::stopping},
    {State::running, Event::drained, State::configured},
    {State::stopping, Event::drained, State::configured},
    {State::idle, Event::error, State::fault},
    {State::configured, Event::error, State::fault},
    {State::calibrating, Event::error, State::fault},
    {State::running, Event::error, State::fault},
    {State::stopping, Event::error, State::fault},
    {State::fault, Event::reset, State::idle},
};

std::optional<State> expected_next(State s, Event e) {
  for (const auto& [from, ev, to] : spec) {
    if (from == s && ev == e) {
      return to;
    }
  }
  return std::nullopt;
}

// Drives a fresh machine into state s through legal events only.
void drive_to(ex::Machine& m, State s) {
  const std::vector<std::vector<Event>> paths{
      {},                                                 // idle
      {Event::configure},                                 // configured
      {Event::configure, Event::calibrate},               // calibrating
      {Event::configure, Event::start},                   // running
      {Event::configure, Event::start, Event::stop},      // stopping
      {Event::error},                                     // fault
  };
  for (Event e : paths[static_cast<std::size_t>(s)]) {
    ASSERT_TRUE(m.apply(e).has_value()) << "cannot reach " << ex::to_string(s);
  }
  ASSERT_EQ(m.state(), s);
}

// Fails the whole process instead of hanging if f deadlocks.
template <typename F>
void within(std::chrono::milliseconds limit, F f, const char* what) {
  auto done = std::make_shared<std::promise<void>>();
  auto fut = done->get_future();
  std::thread([done, f]() mutable {
    f();
    done->set_value();
  }).detach();
  if (fut.wait_for(limit) != std::future_status::ready) {
    std::fprintf(stderr, "watchdog: %s did not finish within %lld ms (deadlock?)\n", what,
                 static_cast<long long>(limit.count()));
    std::_Exit(1);
  }
}

}  // namespace

TEST(StateMachine, NamesAreTheSpecifiedOnes) {
  EXPECT_EQ(ex::to_string(State::calibrating), "calibrating");
  EXPECT_EQ(ex::to_string(State::configured), "configured");
  EXPECT_EQ(ex::to_string(Event::calibrate), "calibrate");
  EXPECT_EQ(ex::to_string(Event::drained), "drained");
  std::set<std::string_view> names;
  for (State s : ex::all_states) {
    names.insert(ex::to_string(s));
  }
  EXPECT_EQ(names.size(), ex::all_states.size()) << "every state has its own name";
}

TEST(StateMachine, EveryStateEventPairFollowsTheSpecification) {
  int legal = 0;
  for (State s : ex::all_states) {
    for (Event e : ex::all_events) {
      EXPECT_EQ(ex::next_state(s, e), expected_next(s, e))
          << ex::to_string(e) << " in state " << ex::to_string(s);
      legal += expected_next(s, e).has_value() ? 1 : 0;
    }
  }
  EXPECT_EQ(legal, 15);
}

TEST(StateMachine, IllegalEventsChangeNothingAndSayWhy) {
  for (State s : ex::all_states) {
    for (Event e : ex::all_events) {
      if (expected_next(s, e)) {
        continue;
      }
      ex::Machine m;
      drive_to(m, s);
      const auto r = m.apply(e);
      ASSERT_FALSE(r.has_value()) << ex::to_string(e) << " in " << ex::to_string(s);
      EXPECT_EQ(r.error().state, s);
      EXPECT_EQ(r.error().event, e);
      EXPECT_EQ(r.error().message(),
                "cannot " + std::string{ex::to_string(e)} + " in state " + std::string{ex::to_string(s)});
      EXPECT_EQ(m.state(), s) << "an illegal event must not change the state";
    }
  }
  EXPECT_EQ((ex::Illegal{State::idle, Event::start}.message()), "cannot start in state idle");
}

TEST(StateMachine, LegalEventsReturnAndStoreTheNewState) {
  for (const auto& [from, e, to] : spec) {
    ex::Machine m;
    drive_to(m, from);
    const auto r = m.apply(e);
    ASSERT_TRUE(r.has_value()) << ex::to_string(e) << " in " << ex::to_string(from);
    EXPECT_EQ(*r, to);
    EXPECT_EQ(m.state(), to);
  }
}

TEST(StateMachine, NoRunWhileCalibratingAndNoResetAwayFromARun) {
  ex::Machine m;
  drive_to(m, State::calibrating);
  EXPECT_FALSE(m.apply(Event::start).has_value()) << "calibration must finish first";
  EXPECT_FALSE(m.apply(Event::configure).has_value());
  ex::Machine r;
  drive_to(r, State::running);
  EXPECT_FALSE(r.apply(Event::reset).has_value()) << "stop and drain first";
}

TEST(StateMachine, ListenerSeesEachTransitionOnceInOrder) {
  std::vector<ex::Transition> seen;
  ex::Machine m{[&](const ex::Transition& t) { seen.push_back(t); }};
  (void)m.apply(Event::configure);
  (void)m.apply(Event::start);    // configured -> running
  (void)m.apply(Event::reset);    // illegal: no call
  (void)m.apply(Event::stop);     // running -> stopping
  (void)m.apply(Event::drained);  // stopping -> configured
  ASSERT_EQ(seen.size(), 4U);
  EXPECT_EQ(seen[0].from, State::idle);
  EXPECT_EQ(seen[1].to, State::running);
  EXPECT_EQ(seen[2].event, Event::stop);
  EXPECT_EQ(seen[3].to, State::configured);
}

TEST(StateMachine, ListenerMayReadTheState) {
  within(
      5'000ms,
      [] {
        std::vector<State> read;
        ex::Machine* self = nullptr;
        ex::Machine m{[&](const ex::Transition&) { read.push_back(self->state()); }};
        self = &m;
        (void)m.apply(Event::configure);
        (void)m.apply(Event::calibrate);
        EXPECT_EQ(read, (std::vector<State>{State::configured, State::calibrating}));
      },
      "a listener calling state()");
}

TEST(StateMachine, ConcurrentEventsGiveOneConsistentHistory) {
  within(
      20'000ms,
      [] {
        std::vector<ex::Transition> history;  // the listener is never called concurrently
        std::atomic<int> in_listener{0};
        std::atomic<bool> overlap{false};
        ex::Machine m{[&](const ex::Transition& t) {
          if (in_listener.fetch_add(1) != 0) {
            overlap = true;
          }
          history.push_back(t);
          in_listener.fetch_sub(1);
        }};
        std::atomic<long> applied{0};
        std::vector<std::thread> threads;
        for (int i = 0; i < 4; ++i) {
          threads.emplace_back([&, i] {
            std::mt19937 rng(static_cast<unsigned>(i) + 1U);
            std::uniform_int_distribution<std::size_t> pick(0, ex::all_events.size() - 1);
            for (int n = 0; n < 20'000; ++n) {
              if (m.apply(ex::all_events[pick(rng)]).has_value()) {
                applied.fetch_add(1);
              }
            }
          });
        }
        for (auto& t : threads) {
          t.join();
        }
        EXPECT_FALSE(overlap.load()) << "listener calls overlapped";
        ASSERT_EQ(static_cast<long>(history.size()), applied.load()) << "one call per transition";
        State expect_from = State::idle;
        for (const auto& t : history) {
          ASSERT_EQ(t.from, expect_from) << "listener calls out of order";
          ASSERT_EQ(expected_next(t.from, t.event), t.to) << "an illegal transition happened";
          expect_from = t.to;
        }
        EXPECT_EQ(m.state(), expect_from);
        EXPECT_GT(history.size(), 1000U);
      },
      "4 threads applying 80,000 events");
}
