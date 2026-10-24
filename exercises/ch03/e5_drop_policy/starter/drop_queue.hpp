// SPDX-License-Identifier: MIT
// Exercise 3.5 starter.
#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>
#include <span>

namespace ex {

enum class Policy { reject, drop_newest, drop_oldest };
enum class PushResult { accepted, rejected, dropped_newest, accepted_evicted_oldest };

struct DropStats {
  std::uint64_t accepted = 0;
  std::uint64_t rejected = 0;
  std::uint64_t dropped_newest = 0;
  std::uint64_t dropped_oldest = 0;
  std::uint64_t popped = 0;
};

// Single-threaded on purpose: the exercise is about policy and accounting.
template <typename T>
class DropQueue {
 public:
  DropQueue(std::size_t capacity, Policy policy) : capacity_{capacity}, policy_{policy} {}

  PushResult push(T value) {
    // TODO
    return PushResult::rejected;
  }
  std::optional<T> pop() {
    // TODO
    return std::nullopt;
  }
  [[nodiscard]] std::size_t size() const noexcept { return q_.size(); }
  [[nodiscard]] const DropStats& stats() const noexcept { return stats_; }

 private:
  std::size_t capacity_;
  Policy policy_;
  std::deque<T> q_;
  DropStats stats_;
};

struct LossReport {
  std::uint64_t lost = 0;
  std::uint64_t out_of_order = 0;
};

inline LossReport count_lost(std::span<const std::uint64_t> seqs, std::uint64_t first) {
  // TODO
  return {};
}

}  // namespace ex
