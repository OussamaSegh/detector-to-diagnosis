// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <fstream>
#include <set>
#include <thread>
#include <tuple>
#include <vector>

#include <nlohmann/json.hpp>

#include "minidaq/control/acquisition_state.hpp"

using namespace minidaq::control;

namespace {
using Key = std::tuple<AcqState, AcqEvent>;
}  // namespace

TEST(AcquisitionState, EveryPairIsEitherInTheTableOrIllegal) {
  // REQ: SRS-CTL-001
  std::set<Key> legal;
  for (const Transition& t : transitions) {
    EXPECT_TRUE(legal.insert({t.from, t.event}).second) << "duplicate " << to_string(t.from) << "/" << to_string(t.event);
  }
  for (const AcqState s : all_states) {
    for (const AcqEvent e : all_events) {
      StateMachine m;
      // Drive the machine into s through legal transitions.
      switch (s) {
        case AcqState::idle: break;
        case AcqState::configured: ASSERT_TRUE(m.apply(AcqEvent::configure)); break;
        case AcqState::running:
          ASSERT_TRUE(m.apply(AcqEvent::configure));
          ASSERT_TRUE(m.apply(AcqEvent::start));
          break;
        case AcqState::stopping:
          ASSERT_TRUE(m.apply(AcqEvent::configure));
          ASSERT_TRUE(m.apply(AcqEvent::start));
          ASSERT_TRUE(m.apply(AcqEvent::stop));
          break;
        case AcqState::fault: ASSERT_TRUE(m.apply(AcqEvent::error)); break;
      }
      ASSERT_EQ(m.state(), s);
      const auto r = m.apply(e);
      if (legal.count({s, e}) != 0) {
        ASSERT_TRUE(r) << to_string(s) << " + " << to_string(e);
        EXPECT_EQ(*r, *next_state(s, e));
        EXPECT_EQ(m.state(), *r);
      } else {
        ASSERT_FALSE(r) << to_string(s) << " + " << to_string(e) << " should be illegal";
        EXPECT_EQ(r.error().state, s);
        EXPECT_EQ(r.error().event, e);
        EXPECT_EQ(m.state(), s) << "an illegal event must not change the state";
      }
    }
  }
}

TEST(AcquisitionState, EveryStateIsReachableAndFaultIsAlwaysRecoverable) {
  // REQ: SRS-CTL-002
  std::set<AcqState> reached{AcqState::idle};
  for (bool grew = true; grew;) {
    grew = false;
    for (const Transition& t : transitions) {
      if (reached.count(t.from) != 0 && reached.insert(t.to).second) {
        grew = true;
      }
    }
  }
  EXPECT_EQ(reached.size(), all_states.size());
  for (const AcqState s : all_states) {
    if (s != AcqState::fault) {
      EXPECT_EQ(next_state(s, AcqEvent::error), AcqState::fault) << to_string(s);
    }
  }
  EXPECT_EQ(next_state(AcqState::fault, AcqEvent::reset), AcqState::idle);
  EXPECT_FALSE(next_state(AcqState::running, AcqEvent::reset)) << "reset must not abort a run silently";
}

TEST(AcquisitionState, TableMatchesTheArchitectureDocument) {
  // The diagram in docs/architecture and Exercise 6.1 are checked against this file.
  std::ifstream in{MINIDAQ_SOURCE_DIR "/docs/architecture/acquisition-states.json"};
  ASSERT_TRUE(in) << "docs/architecture/acquisition-states.json";
  const auto doc = nlohmann::json::parse(in);
  std::set<std::tuple<std::string, std::string, std::string>> want;
  for (const Transition& t : transitions) {
    want.emplace(to_string(t.from), to_string(t.event), to_string(t.to));
  }
  std::set<std::tuple<std::string, std::string, std::string>> got;
  for (const auto& t : doc["transitions"]) {
    got.emplace(t["from"], t["event"], t["to"]);
  }
  EXPECT_EQ(got, want);
  EXPECT_EQ(doc["states"].size(), all_states.size());
  EXPECT_EQ(doc["events"].size(), all_events.size());
}

TEST(AcquisitionState, NamesRoundTrip) {
  for (const AcqState s : all_states) {
    EXPECT_EQ(parse_state(to_string(s)), s);
  }
  for (const AcqEvent e : all_events) {
    EXPECT_EQ(parse_event(to_string(e)), e);
  }
  EXPECT_FALSE(parse_state("Running"));
  EXPECT_EQ(IllegalTransition({AcqState::idle, AcqEvent::start}).message(), "cannot start in state idle");
}

TEST(AcquisitionState, ListenerSeesEveryTransitionAndMayReadTheState) {
  std::vector<Transition> seen;
  StateMachine* self = nullptr;
  StateMachine m{[&](const Transition& t) {
    seen.push_back(t);
    EXPECT_EQ(self->state(), t.to);  // must not deadlock
  }};
  self = &m;
  ASSERT_TRUE(m.apply(AcqEvent::configure));
  ASSERT_FALSE(m.apply(AcqEvent::stop));
  ASSERT_TRUE(m.apply(AcqEvent::start));
  ASSERT_TRUE(m.apply(AcqEvent::error));
  ASSERT_TRUE(m.apply(AcqEvent::reset));
  ASSERT_EQ(seen.size(), 4U) << "illegal events are not transitions";
  EXPECT_EQ(seen[2].event, AcqEvent::error);
  EXPECT_EQ(seen[2].from, AcqState::running);
}

TEST(AcquisitionState, ApplyIfChecksTheExpectedState) {
  StateMachine m;
  ASSERT_TRUE(m.apply(AcqEvent::configure));
  EXPECT_FALSE(m.apply_if(AcqState::idle, AcqEvent::configure));
  EXPECT_EQ(m.state(), AcqState::configured);
  EXPECT_TRUE(m.apply_if(AcqState::configured, AcqEvent::start));
}

TEST(AcquisitionState, ConcurrentEventsAreSerialized) {
  // Four threads race configure/start/stop/drained/reset/error. Whatever the
  // interleaving, the listener must see a chain: each transition starts where
  // the previous one ended.
  // The listener also reads the state, as the service's does: with the state
  // lock held during listener calls this would deadlock (ThreadSanitizer
  // reported the lock-order inversion of an earlier version).
  std::vector<Transition> seen;
  StateMachine* self = nullptr;
  StateMachine m{[&](const Transition& t) {  // listener calls are serialized
    seen.push_back(t);
    (void)self->state();
  }};
  self = &m;
  std::atomic<int> ok{0};
  std::vector<std::jthread> threads;
  for (int k = 0; k < 4; ++k) {
    threads.emplace_back([&, k] {
      for (int i = 0; i < 2000; ++i) {
        const AcqEvent e = all_events[static_cast<std::size_t>((i + k) % 6)];
        if (m.apply(e)) {
          ok.fetch_add(1);
        }
      }
    });
  }
  threads.clear();
  ASSERT_EQ(seen.size(), static_cast<std::size_t>(ok.load()));
  AcqState at = AcqState::idle;
  for (const Transition& t : seen) {
    ASSERT_EQ(t.from, at);
    ASSERT_EQ(next_state(t.from, t.event), t.to);
    at = t.to;
  }
  EXPECT_EQ(m.state(), at);
}
