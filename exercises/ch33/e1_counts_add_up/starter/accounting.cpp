// SPDX-License-Identifier: MIT
#include "accounting.hpp"

namespace ex33 {

std::vector<std::string> accounting_errors(const minidaq::SorterStats& s,
                                           std::span<const minidaq::Coincidence> written) {
  std::vector<std::string> errors;
  if (s.singles_in != s.energy_rejected + s.out_of_order + s.singles_alone + 2 * s.pair_windows +
                          s.singles_in_multiples) {
    errors.emplace_back("singles");
  }
  // TODO: pair windows, multiples, prompts written, delayed written.
  (void)written;
  return errors;
}

}  // namespace ex33
