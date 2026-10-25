// SPDX-License-Identifier: MIT
#include "loss_controls.hpp"

namespace ex152 {

Verdict assess(const Counters& c) {
  Verdict v;
  // TODO: every loss counter, and the fault.
  if (c.packets_lost > 0) {
    v.losses.push_back({"packets_lost", c.packets_lost});
  }
  v.complete = v.losses.empty();
  return v;
}

LossAlarm::LossAlarm(double max_fraction) : max_fraction_{max_fraction} {}

bool LossAlarm::update(std::uint64_t lost_total, std::uint64_t received_total) {
  // TODO: the loss since the last update, latching, a new run.
  raised_ = received_total > 0 &&
            static_cast<double>(lost_total) > max_fraction_ * static_cast<double>(received_total);
  return raised_;
}

}  // namespace ex152
