// SPDX-License-Identifier: MIT
// MiniDAQ - is a run's data complete? (Chapter 15)
//
// Risk control RC-01 for the hazard of silently lost data (docs/regulatory/
// risk/hazards.json): every counter that means data was lost or altered
// between the detector and the disk is collected into one verdict, which the
// service reports in its status and so stores in the run record next to the
// data. A consumer of the data (reconstruction, quality control) reads one
// field instead of knowing every counter, and a run with any loss says so.
#pragma once

#include <nlohmann/json.hpp>

namespace minidaq::control {

// [snippet:api]
// The verdict for one status report (AcquisitionService::status()):
//   {"complete": bool, "losses": [{"counter": "<JSON Pointer>", "count": n}, ...]}
// complete is true only if there was no fault and every loss counter is 0.
// Loss counters: packets lost, rejected or skipped by a resynchronization on
// the readout link; words dropped by any pipeline stage or found invalid by
// the decoder; singles out of time
// order (sort stage and sorter); coincidences the sink could not encode, whose
// energy it clamped, or that it dropped after a fault. A counter that is
// missing from the status (no such port) counts as 0.
[[nodiscard]] nlohmann::json assess_integrity(const nlohmann::json& status);
// [/snippet:api]

}  // namespace minidaq::control
