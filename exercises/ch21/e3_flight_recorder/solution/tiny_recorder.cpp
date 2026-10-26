// SPDX-License-Identifier: MIT
#include "tiny_recorder.hpp"

namespace ex21 {

void TinyRecorder::record(std::uint64_t a, std::uint64_t b) noexcept {
  const std::uint64_t n = next_.load(std::memory_order_relaxed) + 1;  // only this thread writes it
  Slot& s = slots_[(n - 1) % kEvents];
  s.seq.store(2 * n - 1, std::memory_order_relaxed);    // odd: being written
  std::atomic_thread_fence(std::memory_order_release);  // the odd number before the fields
  s.a.store(a, std::memory_order_relaxed);
  s.b.store(b, std::memory_order_relaxed);
  s.seq.store(2 * n, std::memory_order_release);  // even: complete, the fields with it
  next_.store(n, std::memory_order_release);
}

std::size_t TinyRecorder::snapshot(std::span<Event> out) const noexcept {
  const std::uint64_t last = next_.load(std::memory_order_acquire);
  const std::uint64_t first = last > kEvents ? last - kEvents + 1 : 1;
  // The newest out.size() events, from the newest down, then reversed: oldest first.
  std::size_t n = 0;
  std::uint64_t torn = 0;
  for (std::uint64_t e = last; e >= first && e > 0 && n < out.size(); --e) {
    const Slot& s = slots_[(e - 1) % kEvents];
    const std::uint64_t before = s.seq.load(std::memory_order_acquire);
    const std::uint64_t a = s.a.load(std::memory_order_relaxed);
    const std::uint64_t b = s.b.load(std::memory_order_relaxed);
    std::atomic_thread_fence(std::memory_order_acquire);  // the fields before the re-check
    const std::uint64_t after = s.seq.load(std::memory_order_relaxed);
    if (before != 2 * e || after != before) {
      ++torn;  // overwritten by a newer event: so are all older slots
      break;
    }
    out[n++] = Event{e, a, b};
  }
  for (std::size_t i = 0; i < n / 2; ++i) {
    const Event t = out[i];
    out[i] = out[n - 1 - i];
    out[n - 1 - i] = t;
  }
  if (torn > 0) {
    torn_.fetch_add(torn, std::memory_order_relaxed);
  }
  return n;
}

}  // namespace ex21
