// SPDX-License-Identifier: MIT
#include "minidaq/control/acquisition_state.hpp"

namespace minidaq::control {

std::string_view to_string(AcqState s) noexcept {
  switch (s) {
    case AcqState::idle: return "idle";
    case AcqState::configured: return "configured";
    case AcqState::running: return "running";
    case AcqState::stopping: return "stopping";
    case AcqState::fault: return "fault";
  }
  return "?";
}

std::string_view to_string(AcqEvent e) noexcept {
  switch (e) {
    case AcqEvent::configure: return "configure";
    case AcqEvent::start: return "start";
    case AcqEvent::stop: return "stop";
    case AcqEvent::drained: return "drained";
    case AcqEvent::error: return "error";
    case AcqEvent::reset: return "reset";
  }
  return "?";
}

std::optional<AcqState> parse_state(std::string_view s) noexcept {
  for (const AcqState x : all_states) {
    if (to_string(x) == s) {
      return x;
    }
  }
  return std::nullopt;
}

std::optional<AcqEvent> parse_event(std::string_view s) noexcept {
  for (const AcqEvent x : all_events) {
    if (to_string(x) == s) {
      return x;
    }
  }
  return std::nullopt;
}

std::string IllegalTransition::message() const {
  return "cannot " + std::string{to_string(event)} + " in state " + std::string{to_string(state)};
}

AcqState StateMachine::state() const {
  const std::lock_guard lock{mu_};
  return state_;
}

Expected<AcqState, IllegalTransition> StateMachine::apply(AcqEvent e) {
  std::unique_lock lock{mu_};
  return apply_locked(lock, e);
}

Expected<AcqState, IllegalTransition> StateMachine::apply_if(AcqState expected, AcqEvent e) {
  std::unique_lock lock{mu_};
  if (state_ != expected) {
    return Unexpected{IllegalTransition{state_, e}};
  }
  return apply_locked(lock, e);
}

// [snippet:apply]
Expected<AcqState, IllegalTransition> StateMachine::apply_locked(std::unique_lock<std::mutex>& lock, AcqEvent e) {
  const AcqState from = state_;
  const std::optional<AcqState> to = next_state(from, e);
  if (!to) {
    return Unexpected{IllegalTransition{from, e}};
  }
  state_ = *to;
  const std::uint64_t ticket = ++issued_;
  lock.unlock();
  std::unique_lock notify{notify_mu_};
  notify_cv_.wait(notify, [&] { return served_ + 1 == ticket; });
  if (listener_) {
    listener_(Transition{from, e, *to});
  }
  served_ = ticket;
  notify_cv_.notify_all();
  return *to;
}
// [/snippet:apply]

}  // namespace minidaq::control
