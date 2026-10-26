// SPDX-License-Identifier: MIT
#include "handshake.hpp"

namespace hs {

Report check(std::span<const Cycle> trace) {
  Report r;
  for (const Cycle& c : trace) {
    // TODO: count stalls, idle cycles and the longest stall; find the violations of rules 2
    // and 3, which need the previous cycle.
    if (c.valid) {
      ++r.transfers;
    }
  }
  return r;
}

}  // namespace hs
