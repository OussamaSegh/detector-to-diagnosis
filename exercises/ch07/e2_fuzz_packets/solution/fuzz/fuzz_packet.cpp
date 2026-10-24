// SPDX-License-Identifier: MIT
// Exercise 7.2 solution: fuzz target for parse_packet.
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <span>
#include <vector>

#include "packet.hpp"

// [snippet:target]
extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
  const auto packet = std::as_bytes(std::span{data, size});
  const auto info = ex72::parse_packet(packet);
  if (!info) {
    return 0;
  }
  // Read every word the header claims: AddressSanitizer reports any read
  // outside the input, which libFuzzer allocates with exactly `size` bytes.
  std::vector<std::uint64_t> words(info->count);
  if (ex72::read_words(packet, *info, words) != info->count) {
    std::abort();
  }
  // Property: for a plain header, encoding what was parsed gives the input back
  // (up to the ignored trailing bytes).
  if (info->payload_offset == ex72::min_header_bytes) {
    const auto again = ex72::encode_packet(info->board, info->sequence, words);
    if (again.size() > size || std::memcmp(again.data(), data, again.size()) != 0) {
      std::abort();
    }
  }
  return 0;
}
// [/snippet:target]
