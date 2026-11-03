// SPDX-License-Identifier: MIT
#include "minidaq/control/corrections_record.hpp"

#include <string>

namespace minidaq::control {

// REQ: SRS-COR-002
nlohmann::json corrections_record(const SinglesCounter::Snapshot& singles, const SorterConfig& sorter,
                                  const SorterStats& stats) {
  return {{"format", 1},
          {"energy_window_kev", {sorter.energy_low_kev, sorter.energy_high_kev}},
          {"coincidence_window_ps", sorter.window.count()},
          {"window_mode", std::string{to_string(sorter.mode)}},
          {"delayed_window_ps", sorter.delay.count()},
          {"singles_in_window", singles.total},
          {"singles_first_ps", singles.first_ps},
          {"singles_last_ps", singles.last_ps},
          {"singles_per_crystal", singles.per_crystal},
          {"singles_per_block", singles.per_block},
          {"prompts", stats.prompts},
          {"delayeds", stats.delayed}};
}

}  // namespace minidaq::control
