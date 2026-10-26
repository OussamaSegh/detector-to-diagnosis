// SPDX-License-Identifier: MIT
#include "ab_slots.hpp"

namespace ab {

void install(Machine& m, const std::string& version) {
  // TODO: this order runs the new version before it has been checked, writes into the slot that
  // runs on the very first installation, and records the trial after the switch. Find an order in
  // which every power cut leaves a system that starts.
  const std::size_t slot = m.disk().state ? 1 - m.disk().state->good : 0;
  m.switch_current(slot);
  m.extract(slot, version);
  m.check(slot);
  if (!m.disk().state) {
    m.write_state(State{slot, version, std::nullopt, ""});
  } else {
    State s = *m.disk().state;
    s.trial = slot;
    s.trial_version = version;
    m.write_state(s);
  }
}

void confirm(Machine& m) {
  // TODO
  (void)m;
}

void rollback(Machine& m) {
  // TODO: and in which order: the switch or the record first?
  (void)m;
}

std::vector<std::string> repair(Machine& m) {
  // TODO
  (void)m;
  return {};
}

}  // namespace ab
