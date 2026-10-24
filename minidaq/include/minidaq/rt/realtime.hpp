// SPDX-License-Identifier: MIT
// MiniDAQ - real-time profile: pinning, scheduling, memory locking (Chapter 4).
//
// Everything here is Linux-specific and best-effort: on a developer laptop, in
// a container or in CI the calls may fail (no CAP_SYS_NICE, RLIMIT_MEMLOCK too
// small, CPU not present). Failures are returned, never thrown, and the
// pipeline reports them in its status instead of refusing to run. Whether a
// production acquisition may start without its real-time settings is a
// product decision (see the chapter's "In a regulated product" box).
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <system_error>

#include "minidaq/core/expected.hpp"

namespace minidaq::rt {

enum class SchedPolicy : std::uint8_t { other, fifo, rr };

[[nodiscard]] std::string_view to_string(SchedPolicy p) noexcept;

struct StageRt {
  int cpu = -1;                             // -1: do not pin
  SchedPolicy policy = SchedPolicy::other;  // SCHED_OTHER, SCHED_FIFO or SCHED_RR
  int priority = 0;                         // 1..99 for fifo/rr, ignored for other
  friend bool operator==(const StageRt&, const StageRt&) = default;
};

inline constexpr std::size_t max_stages = 5;  // source, decode, sort, pair, write

struct RtProfile {
  bool lock_memory = false;             // mlockall(MCL_CURRENT | MCL_FUTURE)
  std::size_t prefault_stack_bytes = 0;  // touched by each stage thread at start
  std::array<StageRt, max_stages> stages{};
  friend bool operator==(const RtProfile&, const RtProfile&) = default;
};

// What actually happened when a stage applied its settings.
struct StageRtStatus {
  bool applied = false;    // the stage ran apply_stage()
  int requested_cpu = -1;
  int running_cpu = -1;    // sched_getcpu() after pinning
  bool pinned = false;
  bool scheduled = false;  // policy/priority set as requested
  std::error_code error;   // first error, if any
};

// Thread-level settings, for the calling thread.
[[nodiscard]] Expected<void, std::error_code> pin_current_thread(int cpu) noexcept;
[[nodiscard]] Expected<void, std::error_code> set_current_thread_scheduler(SchedPolicy policy, int priority) noexcept;
void name_current_thread(std::string_view name) noexcept;  // truncated to 15 characters
// Timer slack lets the kernel delay timer wake-ups to batch them (50 us by
// default for SCHED_OTHER threads, 0 for real-time ones). 1 ns: wake on time.
[[nodiscard]] Expected<void, std::error_code> set_timer_slack_ns(unsigned long ns) noexcept;
[[nodiscard]] int current_cpu() noexcept;
// Touches `bytes` of stack so that later use does not page-fault.
void prefault_stack(std::size_t bytes) noexcept;
// Applies pinning and scheduling for one stage; never throws.
[[nodiscard]] StageRtStatus apply_stage(const StageRt& s, std::size_t prefault_bytes) noexcept;

// Process-level settings.
[[nodiscard]] Expected<void, std::error_code> lock_all_memory() noexcept;
// Minor and major page faults of the calling thread so far (getrusage RUSAGE_THREAD).
struct PageFaults {
  std::int64_t minor = 0;
  std::int64_t major = 0;
};
[[nodiscard]] PageFaults thread_page_faults() noexcept;

// Profile files are "key = value" lines; '#' starts a comment. Keys:
//   lock_memory = true|false
//   prefault_stack_kib = <n>
//   <stage>.cpu = <n>            stage: source, decode, sort, pair, write
//   <stage>.policy = other|fifo|rr
//   <stage>.priority = <1..99>
struct ProfileError {
  int line = 0;
  std::string message;
};
[[nodiscard]] Expected<RtProfile, ProfileError> parse_profile(std::string_view text);
[[nodiscard]] std::string format_profile(const RtProfile& p);

}  // namespace minidaq::rt
