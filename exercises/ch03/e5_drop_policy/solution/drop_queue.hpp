// SPDX-License-Identifier: MIT
// Exercise 3.5 solution.
#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>
#include <span>
#include <utility>

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

template <typename T>
class DropQueue {
 public:
  DropQueue(std::size_t capacity, Policy policy) : capacity_{capacity}, policy_{policy} {}

  PushResult push(T value) {
    if (q_.size() < capacity_) {
      q_.push_back(std::move(value));
      ++stats_.accepted;
      return PushResult::accepted;
    }
    switch (policy_) {
      case Policy::reject:
        ++stats_.rejected;
        return PushResult::rejected;
      case Policy::drop_newest:
        ++stats_.dropped_newest;
        return PushResult::dropped_newest;
      case Policy::drop_oldest:
        if (capacity_ == 0) {  // nothing to evict: the new item is the one lost
          ++stats_.dropped_newest;
          return PushResult::dropped_newest;
        }
        q_.pop_front();
        ++stats_.dropped_oldest;
        q_.push_back(std::move(value));
        ++stats_.accepted;
        return PushResult::accepted_evicted_oldest;
    }
    return PushResult::rejected;  // unreachable; keeps -Wreturn-type quiet
  }

  std::optional<T> pop() {
    if (q_.empty()) {
      return std::nullopt;
    }
    std::optional<T> v{std::move(q_.front())};
    q_.pop_front();
    ++stats_.popped;
    return v;
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

// Batches carry consecutive sequence numbers from the producer. A jump forward
// by k means k - 1 batches were lost; a number at or below the last one seen is
// a duplicate or a reordering, which is a different fault and counted apart.
inline LossReport count_lost(std::span<const std::uint64_t> seqs, std::uint64_t first) {
  LossReport r;
  std::uint64_t expected = first;
  for (const std::uint64_t s : seqs) {
    if (s >= expected) {
      r.lost += s - expected;
      expected = s + 1;
    } else {
      ++r.out_of_order;
    }
  }
  return r;
}

}  // namespace ex
