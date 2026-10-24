// SPDX-License-Identifier: MIT
// Exercise 7.2: the fuzz target for parse_packet (built by the `fuzz` preset).
#include <cstddef>
#include <cstdint>

#include "packet.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  // TODO: parse the packet; if it is accepted, read all of its words; check
  // that encoding the result gives back the input (for header_words == 2).
  (void)data;
  (void)size;
  return 0;
}
