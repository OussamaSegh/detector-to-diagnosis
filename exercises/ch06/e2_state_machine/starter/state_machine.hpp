// SPDX-License-Identifier: MIT
// Exercise 6.2: an acquisition state machine with a calibration state.
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

namespace ex {

enum class State : std::uint8_t { idle, configured, calibrating, running, stopping, fault };
enum class Event : std::uint8_t { configure, calibrate, start, stop, drained, error, reset };

inline constexpr std::array all_states{State::idle,    State::configured, State::calibrating,
                                       State::running, State::stopping,   State::fault};
inline constexpr std::array all_events{Event::configure, Event::calibrate, Event::start, Event::stop,
                                       Event::drained,   Event::error,     Event::reset};

[[nodiscard]] std::string_view to_string(State s) noexcept;
[[nodiscard]] std::string_view to_string(Event e) noexcept;

struct Transition {
  State from;
  Event event;
  State to;
};

// The next state, or nullopt if `e` is illegal in `from`.
[[nodiscard]] std::optional<State> next_state(State from, Event e) noexcept;

struct Illegal {
  State state;
  Event event;
  // "cannot <event> in state <state>", e.g. "cannot start in state idle".
  [[nodiscard]] std::string message() const;
};

class Machine {
 public:
  using Listener = std::function<void(const Transition&)>;
  explicit Machine(Listener listener = {}) : listener_{std::move(listener)} {}

  [[nodiscard]] State state() const;
  // Applies `e` if legal and returns the new state; otherwise changes nothing.
  // Thread-safe. The listener is called once per transition, in the order the
  // transitions happened, without the state lock held (it may call state()).
  minidaq::Expected<State, Illegal> apply(Event e);

 private:
  mutable std::mutex mu_;
  State state_ = State::idle;
  std::uint64_t issued_ = 0;
  std::mutex notify_mu_;
  std::condition_variable notify_cv_;
  std::uint64_t served_ = 0;
  Listener listener_;
};

}  // namespace ex
