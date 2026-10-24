// SPDX-License-Identifier: MIT
// Exercise 6.4 starter.
#include "frame_reader.hpp"

namespace ex {

std::vector<std::byte> encode_frame(std::span<const std::byte> payload) {
  (void)payload;
  return {};  // TODO: 4-byte big-endian length, then the payload
}

void FrameReader::feed(std::span<const std::byte> bytes) {
  (void)bytes;  // TODO
}

std::optional<std::vector<std::byte>> FrameReader::next() {
  return std::nullopt;  // TODO
}

}  // namespace ex
