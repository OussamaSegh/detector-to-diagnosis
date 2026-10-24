// SPDX-License-Identifier: MIT
// Exercise 6.4 solution.
#include "frame_reader.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

namespace ex {

std::vector<std::byte> encode_frame(std::span<const std::byte> payload) {
  if (payload.size() > std::numeric_limits<std::uint32_t>::max()) {
    throw std::length_error("encode_frame: payload larger than 4 GiB - 1");
  }
  const auto n = static_cast<std::uint32_t>(payload.size());
  std::vector<std::byte> out;
  out.reserve(frame_header_bytes + payload.size());
  for (int shift = 24; shift >= 0; shift -= 8) {
    out.push_back(static_cast<std::byte>((n >> shift) & 0xFFU));
  }
  out.insert(out.end(), payload.begin(), payload.end());
  return out;
}

void FrameReader::feed(std::span<const std::byte> bytes) {
  if (failed_) {
    return;
  }
  // Compact before growing: consumed bytes at the front are dropped in one
  // move, at most once per feed, so the cost stays linear in the bytes received.
  if (start_ > 0 && start_ >= buffer_.size() / 2) {
    buffer_.erase(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(start_));
    start_ = 0;
  }
  buffer_.insert(buffer_.end(), bytes.begin(), bytes.end());
}

// [snippet:next]
std::optional<std::vector<std::byte>> FrameReader::next() {
  if (failed_ || buffered() < frame_header_bytes) {
    return std::nullopt;
  }
  std::uint32_t n = 0;
  for (std::size_t i = 0; i < frame_header_bytes; ++i) {
    n = (n << 8U) | std::to_integer<std::uint32_t>(buffer_[start_ + i]);
  }
  if (n > max_payload_) {
    failed_ = true;  // check before waiting for the payload: never buffer 4 GiB
    buffer_.clear();
    start_ = 0;
    return std::nullopt;
  }
  if (buffered() < frame_header_bytes + n) {
    return std::nullopt;
  }
  const auto first = buffer_.begin() + static_cast<std::ptrdiff_t>(start_ + frame_header_bytes);
  std::vector<std::byte> payload(first, first + n);
  start_ += frame_header_bytes + n;  // consume by moving an index, not by erasing
  if (start_ == buffer_.size()) {
    buffer_.clear();
    start_ = 0;
  }
  return payload;
}
// [/snippet:next]

}  // namespace ex
