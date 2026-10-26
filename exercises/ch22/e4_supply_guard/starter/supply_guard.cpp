// SPDX-License-Identifier: MIT
#include "supply_guard.hpp"

namespace exercise {

bool SupplyGuard::turn_on(double volts, std::int64_t now_ns) {
  // TODO: set the voltage and switch the output on, with bounded retries; the deadline.
  (void)volts;
  (void)now_ns;
  return false;
}

void SupplyGuard::poll(std::int64_t now_ns) {
  // TODO: read and judge the output; in the safe state, make sure the output is off.
  (void)now_ns;
}

bool SupplyGuard::acknowledge() {
  // TODO: only from the safe state, only when the output is known to be off.
  return false;
}

void SupplyGuard::enter_safe(std::string why) {
  // TODO: once, with the first reason; switch the output off.
  (void)why;
}

}  // namespace exercise
