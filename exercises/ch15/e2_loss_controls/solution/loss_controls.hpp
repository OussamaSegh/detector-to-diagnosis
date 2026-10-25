// SPDX-License-Identifier: MIT
// Exercise 15.2: risk controls for silent data loss, without minidaq::control.
// assess() is the acquisition invalidation: one verdict from every loss
// counter and the fault. LossAlarm is the alarm an operator sees during the
// run, before the verdict exists.
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace ex152 {

// The loss counters of one run, as the service collects them.
struct Counters {
  std::uint64_t packets_lost = 0;         // link: sequence numbers declared missing
  std::uint64_t sequence_resyncs = 0;     // link: the source restarted; what it held is unknown
  std::uint64_t packets_rejected = 0;     // link: malformed packets
  std::uint64_t words_invalid = 0;        // decoder: words that decode to no valid single
  std::uint64_t source_dropped = 0;       // pipeline: words dropped under overload
  std::uint64_t sorter_out_of_order = 0;  // sorter: singles too late for their windows
  std::uint64_t sink_invalid = 0;         // sink: coincidences the format cannot hold
  std::uint64_t energies_clamped = 0;     // sink: energies altered to fit the format
  std::uint64_t blocks_dropped = 0;       // sink: blocks dropped after a fault
  std::optional<std::string> fault;       // the run ended in a fault
};

struct Loss {
  std::string counter;  // the field's name in Counters
  std::uint64_t count = 0;
  friend bool operator==(const Loss&, const Loss&) = default;
};

struct Verdict {
  bool complete = true;
  std::vector<Loss> losses;  // every nonzero counter, in the order of Counters
};

// [snippet:assess]
[[nodiscard]] Verdict assess(const Counters& c);
// [/snippet:assess]

// [snippet:alarm]
// Raised when, between two updates, more than max_fraction of the packets
// received were lost. Latched: it stays raised, even once the loss stops,
// until the operator acknowledges it. A counter that goes backward means a new
// run: the alarm starts afresh from it.
class LossAlarm {
 public:
  explicit LossAlarm(double max_fraction);
  // The run's cumulative counters; returns raised().
  bool update(std::uint64_t lost_total, std::uint64_t received_total);
  [[nodiscard]] bool raised() const noexcept { return raised_; }
  void acknowledge() noexcept { raised_ = false; }

 private:
  double max_fraction_;
  std::uint64_t lost_ = 0;
  std::uint64_t received_ = 0;
  bool raised_ = false;
};
// [/snippet:alarm]

}  // namespace ex152
