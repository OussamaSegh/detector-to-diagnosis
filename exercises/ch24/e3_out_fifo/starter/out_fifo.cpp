// SPDX-License-Identifier: MIT
#include "out_fifo.hpp"

namespace fifo {

OutFifo::OutFifo(std::size_t depth) : mem_(depth) {}

std::optional<std::uint64_t> OutFifo::clock(const Inputs& in) {
  // TODO: decide push, pop and the overflow from the state before the edge, then apply them.
  if (in.in_valid && count_ < mem_.size()) {
    mem_[(head_ + count_) % mem_.size()] = in.in_data;
    ++count_;
  }
  return std::nullopt;
}

bool OutFifo::out_valid() const noexcept { return count_ != 0; }
std::size_t OutFifo::level() const noexcept { return count_; }
bool OutFifo::empty() const noexcept { return count_ == 0; }
bool OutFifo::overflow() const noexcept { return overflow_; }
std::uint64_t OutFifo::lost() const noexcept { return lost_; }

std::optional<double> time_to_full_s(std::size_t depth, double in_per_s,
                                     double out_per_s) noexcept {
  (void)depth;
  (void)in_per_s;
  (void)out_per_s;
  return std::nullopt;  // TODO
}

double drain_time_s(std::size_t words, double out_per_s) noexcept {
  (void)words;
  (void)out_per_s;
  return 0;  // TODO
}

std::size_t depth_for_burst(double in_per_s, double out_per_s, double burst_s) noexcept {
  (void)in_per_s;
  (void)out_per_s;
  (void)burst_s;
  return 4096;  // TODO
}

}  // namespace fifo
