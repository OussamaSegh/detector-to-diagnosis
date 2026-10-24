#pragma once
// Exercise 2.5 solution: alignas(64) on the per-stage struct.
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

namespace ex {

inline constexpr std::size_t kStages = 4;
inline constexpr std::size_t kCacheLine = 64;

// alignas on the type makes sizeof(Counters) a multiple of 64 too, so array
// elements cannot share a line.
struct alignas(kCacheLine) Counters {
  std::atomic<std::uint64_t> events_in{0};
  std::atomic<std::uint64_t> events_out{0};
  std::atomic<std::uint64_t> drops{0};
};
static_assert(sizeof(Counters) == kCacheLine);
static_assert(alignof(Counters) == kCacheLine);

class StageCounters {
 public:
  Counters& stage(std::size_t i) { return stages_[i]; }

 private:
  std::array<Counters, kStages> stages_{};
};

}  // namespace ex
