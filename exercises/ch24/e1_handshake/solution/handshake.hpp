// SPDX-License-Identifier: MIT
// Exercise 24.1: check a recorded valid/ready handshake against its rules.
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace hs {

// One clock cycle of a stream, as a logic analyzer or a simulation's waveform records it at the
// rising edge.
struct Cycle {
  bool valid = false;
  bool ready = false;
  std::uint64_t data = 0;
};

struct Report {
  std::size_t transfers = 0;      // cycles where valid and ready are both 1
  std::size_t stalls = 0;         // valid and not ready: the receiver pushed back
  std::size_t idle = 0;           // not valid: the sender had nothing
  std::size_t longest_stall = 0;  // the most consecutive stall cycles
  // One line per broken rule, "cycle N: ...", in the order of the cycles.
  std::vector<std::string> violations;
};

// The rules of the handshake (AXI4-Stream's, which most FPGA streams follow):
//  1. a word moves in a cycle where valid and ready are both 1;
//  2. once valid is 1, it stays 1 until the word has moved ("valid dropped before the transfer");
//  3. while valid is 1 and the word has not moved, data does not change ("data changed while
//     waiting").
// Rule 4, that the sender must not wait for ready before it raises valid, cannot be seen in one
// trace; the NOTES say why it matters.
[[nodiscard]] Report check(std::span<const Cycle> trace);

}  // namespace hs
