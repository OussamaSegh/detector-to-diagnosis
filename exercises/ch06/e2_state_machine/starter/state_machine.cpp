// SPDX-License-Identifier: MIT
// Exercise 6.2 starter: implement the table and the machine.
#include "state_machine.hpp"

namespace ex {

std::string_view to_string(State s) noexcept {
  (void)s;
  return "?";  // TODO
}

std::string_view to_string(Event e) noexcept {
  (void)e;
  return "?";  // TODO
}

std::optional<State> next_state(State from, Event e) noexcept {
  // TODO: one constexpr table of Transition, searched here. Write the table
  // from the README's specification, not from memory of MiniDAQ's.
  (void)from;
  (void)e;
  return std::nullopt;
}

std::string Illegal::message() const {
  return {};  // TODO
}

State Machine::state() const {
  const std::lock_guard lock{mu_};
  return state_;
}

minidaq::Expected<State, Illegal> Machine::apply(Event e) {
  // TODO: apply legal events, call the listener in order and without mu_ held.
  return minidaq::Unexpected{Illegal{state(), e}};
}

}  // namespace ex
