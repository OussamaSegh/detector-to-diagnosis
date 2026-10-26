// SPDX-License-Identifier: MIT
// Exercise 24.2: Gray code, the way a FIFO's pointer crosses from one clock domain to another.
#pragma once

#include <cstdint>

namespace gray {

// Binary to Gray code: consecutive values differ in exactly one bit.
[[nodiscard]] constexpr std::uint32_t encode(std::uint32_t binary) noexcept;
// Gray code back to binary.
[[nodiscard]] std::uint32_t decode(std::uint32_t gray) noexcept;
// How many bits differ between a and b.
[[nodiscard]] int bits_changed(std::uint32_t a, std::uint32_t b) noexcept;

// An asynchronous FIFO of 2^depth_log2 words keeps pointers with one more bit than the address,
// so that full (the pointers differ only in that bit) and empty (equal) can be told apart. The
// read side knows its own pointer in binary and receives the write pointer through a
// synchronizer, in Gray code. Returns how many words the read side may read.
[[nodiscard]] std::uint32_t readable(std::uint32_t write_gray_synced, std::uint32_t read_binary,
                                     unsigned depth_log2) noexcept;

constexpr std::uint32_t encode(std::uint32_t binary) noexcept { return binary ^ (binary >> 1U); }

}  // namespace gray
