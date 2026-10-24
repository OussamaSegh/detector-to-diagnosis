// SPDX-License-Identifier: MIT
// Fuzz target: the configuration reader (Chapter 6). Any text is either
// rejected with at least one error, or accepted; an accepted configuration
// must survive to_json -> parse unchanged and convert to a pipeline config.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string_view>

#include <nlohmann/json.hpp>

#include "minidaq/config/acquisition_config.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  const std::string_view text{reinterpret_cast<const char*>(data), size};
  const auto r = minidaq::config::parse_config(text);
  if (!r) {
    if (r.error().empty()) {
      std::abort();  // rejected without saying why
    }
    return 0;
  }
  const auto again = minidaq::config::parse_config(minidaq::config::to_json(*r).dump());
  if (!again || !(*again == *r)) {
    std::abort();
  }
  (void)minidaq::config::to_pipeline_config(*r);
  return 0;
}
