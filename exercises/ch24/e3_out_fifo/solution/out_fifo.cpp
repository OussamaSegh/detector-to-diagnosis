// SPDX-License-Identifier: MIT
#include "out_fifo.hpp"

#include <cmath>

namespace fifo {

OutFifo::OutFifo(std::size_t depth) : mem_(depth) {}

std::optional<std::uint64_t> OutFifo::clock(const Inputs& in) {
  // Every decision uses the state before the edge, as the flip-flops do.
  const bool full = count_ == mem_.size();
  const bool event = in.in_valid && in.trigger_enable;
  const bool push = event && !full;
  const bool pop = out_valid() && in.out_ready;
  std::optional<std::uint64_t> taken;
  if (pop) {
    taken = mem_[head_];
    head_ = (head_ + 1) % mem_.size();
    --count_;
  }
  if (push) {
    mem_[(head_ + count_) % mem_.size()] = in.in_data;
    ++count_;
  }
  if (event && full) {
    overflow_ = true;  // set wins over clear
    ++lost_;
  } else if (in.overflow_clear) {
    overflow_ = false;
  }
  return taken;
}

bool OutFifo::out_valid() const noexcept { return count_ != 0; }
std::size_t OutFifo::level() const noexcept { return count_; }
bool OutFifo::empty() const noexcept { return count_ == 0; }
bool OutFifo::overflow() const noexcept { return overflow_; }
std::uint64_t OutFifo::lost() const noexcept { return lost_; }

std::optional<double> time_to_full_s(std::size_t depth, double in_per_s,
                                     double out_per_s) noexcept {
  if (in_per_s <= out_per_s) {
    return std::nullopt;
  }
  return static_cast<double>(depth) / (in_per_s - out_per_s);
}

double drain_time_s(std::size_t words, double out_per_s) noexcept {
  return static_cast<double>(words) / out_per_s;
}

std::size_t depth_for_burst(double in_per_s, double out_per_s, double burst_s) noexcept {
  if (in_per_s <= out_per_s) {
    return 1;  // a word in flight still needs a place
  }
  return static_cast<std::size_t>(std::ceil((in_per_s - out_per_s) * burst_s));
}

}  // namespace fifo
