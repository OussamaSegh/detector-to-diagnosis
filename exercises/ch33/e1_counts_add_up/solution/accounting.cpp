// SPDX-License-Identifier: MIT
#include "accounting.hpp"

#include <algorithm>
#include <cstdint>

namespace ex33 {

std::vector<std::string> accounting_errors(const minidaq::SorterStats& s,
                                           std::span<const minidaq::Coincidence> written) {
  using minidaq::CoincidenceKind;
  std::vector<std::string> errors;
  if (s.singles_in != s.energy_rejected + s.out_of_order + s.singles_alone + 2 * s.pair_windows +
                          s.singles_in_multiples) {
    errors.emplace_back("singles");
  }
  if (s.prompts + s.geometry_rejected != s.pair_windows) {
    errors.emplace_back("pair windows");
  }
  if (s.prompts_from_multiples != 0 || 3 * s.multiple_windows > s.singles_in_multiples ||
      (s.multiple_windows == 0) != (s.singles_in_multiples == 0)) {
    errors.emplace_back("multiples");
  }
  const auto count = [&](CoincidenceKind k) {
    return static_cast<std::uint64_t>(
        std::ranges::count_if(written, [k](const minidaq::Coincidence& c) { return c.kind == k; }));
  };
  if (count(CoincidenceKind::prompt) != s.prompts) {
    errors.emplace_back("prompts written");
  }
  if (count(CoincidenceKind::delayed) != s.delayed) {
    errors.emplace_back("delayed written");
  }
  return errors;
}

}  // namespace ex33
