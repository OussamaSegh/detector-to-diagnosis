// SPDX-License-Identifier: MIT
// MiniDAQ - what this build of the control plane contains (CR-0029). A product build
// (CMake option MINIDAQ_WITH_SIMULATOR off) has no simulator: no synthetic source and no
// simulated front-end boards, and it refuses a configuration that asks for them.
#pragma once

#ifndef MINIDAQ_WITH_SIMULATOR
#define MINIDAQ_WITH_SIMULATOR 1
#endif

namespace minidaq::control {

inline constexpr bool with_simulator = MINIDAQ_WITH_SIMULATOR != 0;
// The refusal of a product build, the same words for the source and the boards.
inline constexpr const char* no_simulator_in_product =
    "this is a product build: the simulator is not part of it";

}  // namespace minidaq::control
