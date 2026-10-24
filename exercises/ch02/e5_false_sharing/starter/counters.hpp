#pragma once
// Exercise 2.5 starter. TODO: keep each stage's counters on its own cache line.
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace ex {

inline constexpr std::size_t kStages = 4;

struct Counters {
  std::atomic<std::uint64_t> events_in{0};
  std::atomic<std::uint64_t> events_out{0};
  std::atomic<std::uint64_t> drops{0};
};

class StageCounters {
 public:
  Counters& stage(std::size_t i) { return stages_[i]; }

 private:
  std::array<Counters, kStages> stages_{};  // 24 bytes each: neighbours share lines
};

}  // namespace ex
