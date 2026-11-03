// SPDX-License-Identifier: MIT
// MiniDAQ - what the run record carries for the corrections (Chapter 27).
//
// The list-mode file holds the coincidences. The randoms estimate from the singles and the
// dead-time model need the singles of each crystal as well, and every correction needs the
// windows the sorter used. The service adds this object to the run record when the run ends
// (SRS-COR-002); minidaq_sim writes the same object for a simulated run.
#pragma once

#include <nlohmann/json.hpp>

#include "minidaq/processing/coincidence_sorter.hpp"
#include "minidaq/processing/singles_counter.hpp"

namespace minidaq::control {

// [snippet:api]
//   {"format": 1,
//    "energy_window_kev": [low, high], "coincidence_window_ps": w, "window_mode": "fixed",
//    "delayed_window_ps": d,
//    "singles_in_window": n, "singles_first_ps": t0, "singles_last_ps": t1,
//    "singles_per_crystal": [18,432 counts, crystal id order],
//    "singles_per_block": [72 counts, every energy, block id order],
//    "prompts": p, "delayeds": q}
// The singles per crystal are those in the energy window, counted after the calibration; the
// singles per block are all of them, which is what the dead time of a block's electronics depends
// on; t0 and t1 are the earliest and latest time of any single (0 and 0 if there were none).
[[nodiscard]] nlohmann::json corrections_record(const SinglesCounter::Snapshot& singles,
                                                const SorterConfig& sorter, const SorterStats& stats);
// [/snippet:api]

}  // namespace minidaq::control
