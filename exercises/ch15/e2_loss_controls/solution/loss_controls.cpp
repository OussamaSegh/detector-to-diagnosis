// SPDX-License-Identifier: MIT
#include "loss_controls.hpp"

#include <stdexcept>

namespace ex152 {

Verdict assess(const Counters& c) {
  Verdict v;
  const auto add = [&v](const char* name, std::uint64_t n) {
    if (n > 0) {
      v.losses.push_back({name, n});
    }
  };
  add("packets_lost", c.packets_lost);
  add("sequence_resyncs", c.sequence_resyncs);
  add("packets_rejected", c.packets_rejected);
  add("words_invalid", c.words_invalid);
  add("source_dropped", c.source_dropped);
  add("sorter_out_of_order", c.sorter_out_of_order);
  add("sink_invalid", c.sink_invalid);
  add("energies_clamped", c.energies_clamped);
  add("blocks_dropped", c.blocks_dropped);
  v.complete = v.losses.empty() && !c.fault;
  return v;
}

LossAlarm::LossAlarm(double max_fraction) : max_fraction_{max_fraction} {
  if (!(max_fraction >= 0.0 && max_fraction < 1.0)) {
    throw std::invalid_argument{"max_fraction must be in [0, 1)"};
  }
}

// [snippet:update]
bool LossAlarm::update(std::uint64_t lost_total, std::uint64_t received_total) {
  if (lost_total < lost_ || received_total < received_) {
    lost_ = 0;  // a new run: its counters started again from 0
    received_ = 0;
  }
  const std::uint64_t lost = lost_total - lost_;
  const std::uint64_t received = received_total - received_;
  lost_ = lost_total;
  received_ = received_total;
  // Lost packets were never received, so the packets the source sent are both.
  const std::uint64_t sent = lost + received;
  if (sent > 0 && static_cast<double>(lost) > max_fraction_ * static_cast<double>(sent)) {
    raised_ = true;
  }
  return raised_;
}
// [/snippet:update]

}  // namespace ex152
