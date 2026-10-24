// SPDX-License-Identifier: MIT
// MiniDAQ - the acquisition state machine (Chapter 6).
//
//   idle       --configure--> configured --start--> running --stop--> stopping
//   configured --configure--> configured (reconfigure), --reset--> idle
//   running    --drained--> configured   (a finite run ended by itself)
//   stopping   --drained--> configured   (in-flight data written)
//   any state but fault --error--> fault --reset--> idle
//
// The table below is the single source of truth: the service, the control
// API, the documentation diagram and the tests all use it. A transition that
// is not in the table is illegal and leaves the state unchanged.
#pragma once

#include <array>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>

#include "minidaq/core/expected.hpp"

namespace minidaq::control {

enum class AcqState : std::uint8_t { idle, configured, running, stopping, fault };
// configure, start, stop and reset come from an operator (the control API);
// drained and error come from the system (the pipeline or a device).
enum class AcqEvent : std::uint8_t { configure, start, stop, drained, error, reset };

inline constexpr std::array all_states{AcqState::idle, AcqState::configured, AcqState::running,
                                       AcqState::stopping, AcqState::fault};
inline constexpr std::array all_events{AcqEvent::configure, AcqEvent::start, AcqEvent::stop,
                                       AcqEvent::drained,   AcqEvent::error, AcqEvent::reset};

[[nodiscard]] std::string_view to_string(AcqState s) noexcept;
[[nodiscard]] std::string_view to_string(AcqEvent e) noexcept;
[[nodiscard]] std::optional<AcqState> parse_state(std::string_view s) noexcept;
[[nodiscard]] std::optional<AcqEvent> parse_event(std::string_view s) noexcept;

struct Transition {
  AcqState from;
  AcqEvent event;
  AcqState to;
};

// [snippet:table]
inline constexpr std::array transitions{
    Transition{AcqState::idle, AcqEvent::configure, AcqState::configured},
    Transition{AcqState::configured, AcqEvent::configure, AcqState::configured},  // reconfigure
    Transition{AcqState::configured, AcqEvent::start, AcqState::running},
    Transition{AcqState::configured, AcqEvent::reset, AcqState::idle},
    Transition{AcqState::running, AcqEvent::stop, AcqState::stopping},
    Transition{AcqState::running, AcqEvent::drained, AcqState::configured},  // finite run ended
    Transition{AcqState::stopping, AcqEvent::drained, AcqState::configured},
    Transition{AcqState::idle, AcqEvent::error, AcqState::fault},
    Transition{AcqState::configured, AcqEvent::error, AcqState::fault},
    Transition{AcqState::running, AcqEvent::error, AcqState::fault},
    Transition{AcqState::stopping, AcqEvent::error, AcqState::fault},
    Transition{AcqState::fault, AcqEvent::reset, AcqState::idle},
};
// [/snippet:table]

[[nodiscard]] constexpr std::optional<AcqState> next_state(AcqState from, AcqEvent e) noexcept {
  for (const Transition& t : transitions) {
    if (t.from == from && t.event == e) {
      return t.to;
    }
  }
  return std::nullopt;
}

struct IllegalTransition {
  AcqState state;
  AcqEvent event;
  [[nodiscard]] std::string message() const;
};

// Thread-safe holder of the current state. Listeners run after the state has
// changed, outside the lock, in the order the transitions happened; they may
// call state() but must not call apply() (a listener that needs to react with
// an event does so from another thread).
class StateMachine {
 public:
  using Listener = std::function<void(const Transition&)>;

  explicit StateMachine(Listener on_transition = {}) : listener_{std::move(on_transition)} {}

  [[nodiscard]] AcqState state() const;
  // Applies e if it is legal in the current state and returns the new state;
  // otherwise returns the error and changes nothing.
  Expected<AcqState, IllegalTransition> apply(AcqEvent e);
  // Applies e only if the current state is `expected`; used by code that
  // decided on an event while not holding the lock.
  Expected<AcqState, IllegalTransition> apply_if(AcqState expected, AcqEvent e);

 private:
  Expected<AcqState, IllegalTransition> apply_locked(std::unique_lock<std::mutex>& lock, AcqEvent e);

  mutable std::mutex mu_;
  AcqState state_ = AcqState::idle;
  std::uint64_t issued_ = 0;  // transitions made (under mu_)
  // Listener calls happen in transition order: each transition takes a ticket
  // under mu_, then waits, without holding mu_, until the previous ticket has
  // been served. mu_ is never held while notify_mu_ is taken, so a listener
  // may call state() without a lock-order inversion.
  std::mutex notify_mu_;
  std::condition_variable notify_cv_;
  std::uint64_t served_ = 0;  // under notify_mu_
  Listener listener_;
};

}  // namespace minidaq::control
