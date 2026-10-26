// SPDX-License-Identifier: MIT
#include "minidaq/hw/register.hpp"

namespace minidaq::hw {

std::string_view to_string(HwErrc e) noexcept {
  switch (e) {
    case HwErrc::ok:
      return "ok";
    case HwErrc::timeout:
      return "timeout";
    case HwErrc::bus_error:
      return "bus error";
    case HwErrc::bad_address:
      return "bad address";
  }
  return "unknown";
}

}  // namespace minidaq::hw
