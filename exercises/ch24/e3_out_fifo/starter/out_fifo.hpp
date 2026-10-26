// SPDX-License-Identifier: MIT
// Exercise 24.3: the board's output FIFO, cycle by cycle, and how deep a FIFO must be.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace fifo {

// What hw/rtl/feb_out_fifo.sv does at each rising clock edge, as software. The FIFO holds
// `depth` words. An event that finds it full is lost and sets the sticky overflow flag, even if
// the link takes a word in the same cycle; a clear in the same cycle as a lost event leaves the
// flag set; nothing enters while the triggers are off.
class OutFifo {
 public:
  explicit OutFifo(std::size_t depth);

  struct Inputs {
    bool trigger_enable = false;
    bool in_valid = false;
    std::uint64_t in_data = 0;
    bool out_ready = false;
    bool overflow_clear = false;
  };
  // One rising edge. Returns the word the link took at this edge, if any.
  std::optional<std::uint64_t> clock(const Inputs& in);

  // The outputs between edges.
  [[nodiscard]] bool out_valid() const noexcept;
  [[nodiscard]] std::size_t level() const noexcept;
  [[nodiscard]] bool empty() const noexcept;  // STATUS.FIFO_EMPTY
  [[nodiscard]] bool overflow() const noexcept;
  [[nodiscard]] std::uint64_t lost() const noexcept;  // events lost so far (the flag cannot count)

 private:
  std::vector<std::uint64_t> mem_;
  std::size_t head_ = 0;
  std::size_t count_ = 0;
  bool overflow_ = false;
  std::uint64_t lost_ = 0;
};

// How long a FIFO of `depth` words takes to fill from empty when words come in at `in_per_s` and
// leave at `out_per_s`; empty when it never fills.
[[nodiscard]] std::optional<double> time_to_full_s(std::size_t depth, double in_per_s,
                                                   double out_per_s) noexcept;
// How long `words` take to leave at `out_per_s`, once nothing comes in.
[[nodiscard]] double drain_time_s(std::size_t words, double out_per_s) noexcept;
// The smallest depth that loses nothing in a burst of `burst_s` seconds at `in_per_s` while the
// link sends `out_per_s`.
[[nodiscard]] std::size_t depth_for_burst(double in_per_s, double out_per_s,
                                          double burst_s) noexcept;

}  // namespace fifo
