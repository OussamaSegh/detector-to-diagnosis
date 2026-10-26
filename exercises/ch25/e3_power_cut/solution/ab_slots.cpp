// SPDX-License-Identifier: MIT
#include "ab_slots.hpp"

namespace ab {

// [snippet:install]
void install(Machine& m, const std::string& version) {
  const auto& state = m.disk().state;
  const std::size_t slot = state ? 1 - state->good : 0;
  // Into the slot that does not run, checked before anything points at it.
  m.extract(slot, version);
  m.check(slot);
  // Recorded before the switch: a cut between the two leaves a trial that is not current, which
  // repair() discards; the good version still runs.
  State next = state.value_or(State{slot, version, std::nullopt, ""});
  if (state) {
    next.trial = slot;
    next.trial_version = version;
  }
  m.write_state(next);
  m.switch_current(slot);
}
// [/snippet:install]

void confirm(Machine& m) {
  const auto& state = m.disk().state;
  if (!state || !state->trial) {
    return;
  }
  m.write_state(State{*state->trial, state->trial_version, std::nullopt, ""});
}

// [snippet:rollback]
void rollback(Machine& m) {
  const auto& state = m.disk().state;
  if (!state || !state->trial) {
    return;
  }
  // Switched first: a cut after the switch leaves a trial that is not current, which repair()
  // discards. Recorded first, a cut would leave the trial running as if it were confirmed.
  m.switch_current(state->good);
  m.write_state(State{state->good, state->good_version, std::nullopt, ""});
}
// [/snippet:rollback]

std::vector<std::string> repair(Machine& m) {
  std::vector<std::string> done;
  const auto& disk = m.disk();
  if (!disk.state) {
    return done;  // nothing installed; current cannot be set without a state (install writes it
                  // first)
  }
  if (!disk.current) {
    m.switch_current(disk.state->good);  // a first installation cut between its record and switch
    done.emplace_back("current set to the good slot");
  }
  if (disk.state->trial && *disk.state->trial != *disk.current) {
    State s = *disk.state;  // an install cut before its switch, or a rollback after it
    s.trial.reset();
    s.trial_version.clear();
    m.write_state(s);
    done.emplace_back("trial discarded: it is not current");
  }
  return done;
}

}  // namespace ab
