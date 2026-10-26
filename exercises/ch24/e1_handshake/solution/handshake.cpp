// SPDX-License-Identifier: MIT
#include "handshake.hpp"

#include <algorithm>

namespace hs {

Report check(std::span<const Cycle> trace) {
  Report r;
  std::size_t run = 0;
  for (std::size_t i = 0; i < trace.size(); ++i) {
    const Cycle& c = trace[i];
    // A word was waiting at the previous edge: valid and data must still be there.
    if (i > 0 && trace[i - 1].valid && !trace[i - 1].ready) {
      const std::string at = "cycle " + std::to_string(i) + ": ";
      if (!c.valid) {
        r.violations.push_back(at + "valid dropped before the transfer");
      } else if (c.data != trace[i - 1].data) {
        r.violations.push_back(at + "data changed while waiting");
      }
    }
    if (c.valid && c.ready) {
      ++r.transfers;
      run = 0;
    } else if (c.valid) {
      ++r.stalls;
      r.longest_stall = std::max(r.longest_stall, ++run);
    } else {
      ++r.idle;
      run = 0;
    }
  }
  return r;
}

}  // namespace hs
