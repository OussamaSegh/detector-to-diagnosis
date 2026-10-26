// SPDX-License-Identifier: MIT
// Exercise 24.4: read a 64-bit counter that the board exposes as two 32-bit registers while it
// keeps counting.
#pragma once

#include <cstdint>
#include <optional>

namespace split {

// The part of a register bus this exercise needs: one aligned 32-bit read, which fails when the
// board does not answer.
class Bus {
 public:
  virtual ~Bus() = default;
  virtual std::optional<std::uint32_t> read32(std::uint32_t address) = 0;
};

// Reads the counter whose low half is at `lo_address` and high half at `hi_address`. The result
// is a value the counter really held during the call, never a mix of two values. Empty when a
// read fails, or when `attempts` tries in a row saw the high half change.
[[nodiscard]] std::optional<std::uint64_t> read_counter(Bus& bus, std::uint32_t lo_address,
                                                        std::uint32_t hi_address, int attempts = 3);

}  // namespace split
