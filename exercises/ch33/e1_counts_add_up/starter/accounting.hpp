// SPDX-License-Identifier: MIT
// Exercise 33.1: the conservation equations of the coincidence sorter.
#pragma once

#include <span>
#include <string>
#include <vector>

#include "minidaq/core/single.hpp"
#include "minidaq/processing/coincidence_sorter.hpp"

namespace ex33 {

// The names of the equations that do not hold, in the order of the README, for a sorter in
// fixed mode with the kill_all policy, after flush(): `s` is its counters and `written` the
// coincidences it gave. Empty when every count adds up.
[[nodiscard]] std::vector<std::string> accounting_errors(
    const minidaq::SorterStats& s, std::span<const minidaq::Coincidence> written);

}  // namespace ex33
