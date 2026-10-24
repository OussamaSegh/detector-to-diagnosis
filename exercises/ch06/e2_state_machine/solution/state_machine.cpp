// SPDX-License-Identifier: MIT
// Exercise 6.2 solution.
#include "state_machine.hpp"

namespace ex {

namespace {

// [snippet:table]
constexpr std::array table{
    Transition{State::idle, Event::configure, State::configured},
    Transition{State::configured, Event::configure, State::configured},
    Transition{State::configured, Event::calibrate, State::calibrating},
    Transition{State::calibrating, Event::drained, State::configured},  // calibration finished
    Transition{State::configured, Event::start, State::running},
    Transition{State::configured, Event::reset, State::idle},
    Transition{State::running, Event::stop, State::stopping},
    Transition{State::running, Event::drained, State::configured},
    Transition{State::stopping, Event::drained, State::configured},
    Transition{State::idle, Event::error, State::fault},
    Transition{State::configured, Event::error, State::fault},
    Transition{State::calibrating, Event::error, State::fault},
    Transition{State::running, Event::error, State::fault},
    Transition{State::stopping, Event::error, State::fault},
    Transition{State::fault, Event::reset, State::idle},
};
// [/snippet:table]

}  // namespace

std::string_view to_string(State s) noexcept {
  switch (s) {
    case State::idle: return "idle";
    case State::configured: return "configured";
    case State::calibrating: return "calibrating";
    case State::running: return "running";
    case State::stopping: return "stopping";
    case State::fault: return "fault";
  }
  return "?";
}

std::string_view to_string(Event e) noexcept {
  switch (e) {
    case Event::configure: return "configure";
    case Event::calibrate: return "calibrate";
    case Event::start: return "start";
    case Event::stop: return "stop";
    case Event::drained: return "drained";
    case Event::error: return "error";
    case Event::reset: return "reset";
  }
  return "?";
}

std::optional<State> next_state(State from, Event e) noexcept {
  for (const Transition& t : table) {
    if (t.from == from && t.event == e) {
      return t.to;
    }
  }
  return std::nullopt;
}

std::string Illegal::message() const {
  return "cannot " + std::string{to_string(event)} + " in state " + std::string{to_string(state)};
}

State Machine::state() const {
  const std::lock_guard lock{mu_};
  return state_;
}

// [snippet:apply]
minidaq::Expected<State, Illegal> Machine::apply(Event e) {
  std::unique_lock lock{mu_};
  const State from = state_;
  const auto to = next_state(from, e);
  if (!to) {
    return minidaq::Unexpected{Illegal{from, e}};
  }
  state_ = *to;
  const std::uint64_t ticket = ++issued_;  // our place in the order of transitions
  lock.unlock();                           // never hold mu_ while taking notify_mu_

  std::unique_lock notify{notify_mu_};
  notify_cv_.wait(notify, [&] { return served_ + 1 == ticket; });
  if (listener_) {
    listener_(Transition{from, e, *to});
  }
  served_ = ticket;
  notify.unlock();
  notify_cv_.notify_all();
  return *to;
}
// [/snippet:apply]

}  // namespace ex
