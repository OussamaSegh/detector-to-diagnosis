// SPDX-License-Identifier: MIT
// Fuzz target: the raw16 debug-record parser (Chapter 1). A record that parses
// must serialize back to the same 16 bytes.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>

#include "minidaq/format/raw_single.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  const auto bytes = std::span{reinterpret_cast<const std::byte*>(data), size};
  const auto r = minidaq::parse_single(bytes);
  if (r) {
    const auto again = minidaq::serialize_raw16(*r);
    const auto back = minidaq::parse_single(again);
    if (!back || !(*back == *r)) {
      std::abort();
    }
  }
  return 0;
}
