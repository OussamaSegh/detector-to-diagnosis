// SPDX-License-Identifier: MIT
// MiniDAQ - waiting strategy for pipeline stages (Chapters 3 and 4).
//
// A stage with nothing to do first spins (cheapest wake-up, burns a core),
// then yields its time slice, then sleeps for short intervals. On an isolated
// core in the real-time profile (Chapter 4) you would spin only; on a shared
// development machine or in CI, sleeping keeps idle stages from starving the
// busy ones.
#pragma once

#include <chrono>
#include <cstdint>
#include <thread>

namespace minidaq {

struct BackoffPolicy {
  std::uint32_t spins = 64;
  std::uint32_t yields = 16;
  std::chrono::microseconds sleep{20};
};

class Backoff {
 public:
  explicit Backoff(BackoffPolicy p = {}) noexcept : p_{p} {}
  void pause() noexcept {
    if (n_ < p_.spins) {
      cpu_relax();
    } else if (n_ < p_.spins + p_.yields) {
      std::this_thread::yield();
    } else {
      std::this_thread::sleep_for(p_.sleep);
    }
    ++n_;
  }
  void reset() noexcept { n_ = 0; }

 private:
  static void cpu_relax() noexcept {
#if defined(__x86_64__) || defined(__i386__)
    __builtin_ia32_pause();  // PAUSE: tells the core we are spinning
#elif defined(__aarch64__)
    asm volatile("yield" ::: "memory");
#endif
  }
  BackoffPolicy p_;
  std::uint32_t n_ = 0;
};

}  // namespace minidaq
