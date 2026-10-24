// SPDX-License-Identifier: MIT
// Exercise 6.4: framing for a binary, length-prefixed protocol.
//
// A frame is a 4-byte unsigned length in network byte order (big-endian),
// followed by that many payload bytes. TCP delivers a byte stream: one read
// can hold half a header, or a thousand frames.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace ex {

inline constexpr std::size_t frame_header_bytes = 4;

[[nodiscard]] std::vector<std::byte> encode_frame(std::span<const std::byte> payload);

class FrameReader {
 public:
  explicit FrameReader(std::size_t max_payload) : max_payload_{max_payload} {}

  // Appends received bytes. Ignored once failed().
  void feed(std::span<const std::byte> bytes);
  // The next complete payload, or nullopt if none is complete yet (or failed()).
  [[nodiscard]] std::optional<std::vector<std::byte>> next();
  // True once a header announced more than max_payload bytes. Permanent: after
  // a bad length there is no way to find the next frame boundary.
  [[nodiscard]] bool failed() const noexcept { return failed_; }
  // Bytes received but not yet returned as frames.
  [[nodiscard]] std::size_t buffered() const noexcept { return buffer_.size() - start_; }

 private:
  std::size_t max_payload_;
  std::vector<std::byte> buffer_;
  std::size_t start_ = 0;  // first unconsumed byte of buffer_
  bool failed_ = false;
};

}  // namespace ex
