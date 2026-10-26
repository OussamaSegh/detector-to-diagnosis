// SPDX-License-Identifier: MIT
#include "minidaq/core/flight_recorder.hpp"

#include <algorithm>
#include <ctime>

namespace minidaq {

std::string_view to_string(TraceCode c) noexcept {
  switch (c) {
    case TraceCode::state:
      return "state";
    case TraceCode::command:
      return "command";
    case TraceCode::run_begin:
      return "run_begin";
    case TraceCode::run_end:
      return "run_end";
    case TraceCode::link_gap:
      return "link_gap";
    case TraceCode::fault:
      return "fault";
    case TraceCode::link_resync:
      return "link_resync";
    case TraceCode::note:
      return "note";
    case TraceCode::none:
      break;
  }
  return "none";
}

namespace {

// Order of a snapshot: by time, then by ring and by number within the ring for equal times.
bool later(const TraceEvent& x, const TraceEvent& y) noexcept {
  if (x.t_ns != y.t_ns) {
    return x.t_ns > y.t_ns;
  }
  return x.ring != y.ring ? x.ring > y.ring : x.seq > y.seq;
}

std::uint64_t now_ns() noexcept {
  timespec ts{};
  (void)clock_gettime(CLOCK_MONOTONIC, &ts);  // cannot fail for CLOCK_MONOTONIC; signal-safe
  return static_cast<std::uint64_t>(ts.tv_sec) * 1'000'000'000U + static_cast<std::uint64_t>(ts.tv_nsec);
}

}  // namespace

// A thread's rings, one per recorder it has recorded into, given back when the thread exits.
// A recorder must outlive every thread that records into it (static storage in practice).
struct RingLease {
  static constexpr std::size_t kMax = 4;
  struct Entry {
    FlightRecorder* recorder = nullptr;
    FlightRecorder::Ring* ring = nullptr;
  };
  std::array<Entry, kMax> entries{};

  RingLease() = default;
  RingLease(const RingLease&) = delete;
  RingLease& operator=(const RingLease&) = delete;
  RingLease(RingLease&&) = delete;
  RingLease& operator=(RingLease&&) = delete;
  ~RingLease() {
    for (const auto& e : entries) {
      if (e.ring != nullptr) {
        e.ring->owned.store(false, std::memory_order_release);
      }
    }
  }

  FlightRecorder::Ring* find(FlightRecorder* r) noexcept {
    for (auto& e : entries) {
      if (e.recorder == r) {
        return e.ring;
      }
      if (e.recorder == nullptr) {
        e.recorder = r;
        e.ring = r->claim();  // may be nullptr: all rings taken; the thread's events are dropped
        return e.ring;
      }
    }
    return nullptr;
  }
};

namespace {
thread_local RingLease lease;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables): one per thread by design
}  // namespace

FlightRecorder::Ring* FlightRecorder::claim() noexcept {
  for (auto& ring : rings_) {
    bool expected = false;
    if (ring.owned.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
      return &ring;
    }
  }
  return nullptr;
}

// [snippet:record]
void FlightRecorder::record(TraceCode code, std::uint64_t a, std::uint64_t b) noexcept {
  Ring* ring = lease.find(this);
  if (ring == nullptr) {
    dropped_.fetch_add(1, std::memory_order_relaxed);
    return;
  }
  // Only this thread writes this ring, so `next` needs no read-modify-write.
  const std::uint64_t n = ring->next.load(std::memory_order_relaxed);
  Slot& s = ring->slots[n & (kRingEvents - 1)];
  s.seq.store(2 * n + 1, std::memory_order_relaxed);    // odd: being written
  std::atomic_thread_fence(std::memory_order_release);  // ...before any of the fields below
  s.t_ns.store(now_ns(), std::memory_order_relaxed);
  s.a.store(a, std::memory_order_relaxed);
  s.b.store(b, std::memory_order_relaxed);
  s.code.store(static_cast<std::uint8_t>(code), std::memory_order_relaxed);
  s.seq.store(2 * n + 2, std::memory_order_release);  // even: complete, and the fields with it
  ring->next.store(n + 1, std::memory_order_release);  // also the count of recorded events
}
// [/snippet:record]

// [snippet:snapshot]
bool FlightRecorder::read_slot(const Ring& ring, std::uint64_t n, TraceEvent& e) noexcept {
  const Slot& s = ring.slots[n & (kRingEvents - 1)];
  const std::uint64_t before = s.seq.load(std::memory_order_acquire);
  e.t_ns = s.t_ns.load(std::memory_order_relaxed);
  e.a = s.a.load(std::memory_order_relaxed);
  e.b = s.b.load(std::memory_order_relaxed);
  e.code = static_cast<TraceCode>(s.code.load(std::memory_order_relaxed));
  std::atomic_thread_fence(std::memory_order_acquire);  // the fields before the re-check
  const std::uint64_t after = s.seq.load(std::memory_order_relaxed);
  e.seq = n + 1;
  // Event n is complete when its slot says 2n+2 before and after the copy. Anything else means
  // the writer was overwriting the slot with a newer event while we copied it.
  return before == 2 * n + 2 && after == before;
}

std::size_t FlightRecorder::snapshot_into(std::span<TraceEvent> out) noexcept {
  // A merge of the rings from their newest events backwards: each ring is in time order, so
  // the newest event overall is the newest head of some ring. Cost: out.size() x kRings slot
  // reads at most, without allocation (the cursors are on the stack).
  std::array<std::uint64_t, kRings> left{};  // events of ring r not yet taken: n < left[r]
  std::array<std::uint64_t, kRings> oldest{};
  std::array<TraceEvent, kRings> head{};
  std::array<bool, kRings> has{};
  std::uint64_t torn = 0;
  auto advance = [&](std::size_t r) noexcept {
    has[r] = false;
    while (left[r] > oldest[r]) {
      --left[r];
      if (read_slot(rings_[r], left[r], head[r])) {
        head[r].ring = static_cast<std::uint32_t>(r);
        has[r] = true;
        return;
      }
      ++torn;
      left[r] = oldest[r];  // overwritten: the older slots of this ring are newer events too
    }
  };
  for (std::size_t r = 0; r < kRings; ++r) {
    left[r] = rings_[r].next.load(std::memory_order_acquire);
    oldest[r] = left[r] > kRingEvents ? left[r] - kRingEvents : 0;
    advance(r);
  }
  std::size_t n = 0;
  while (n < out.size()) {
    std::size_t best = kRings;
    for (std::size_t r = 0; r < kRings; ++r) {
      if (has[r] && (best == kRings || later(head[r], head[best]))) {
        best = r;
      }
    }
    if (best == kRings) {
      break;  // every ring is exhausted
    }
    out[n++] = head[best];
    advance(best);
  }
  std::reverse(out.begin(), out.begin() + static_cast<std::ptrdiff_t>(n));  // oldest first
  if (torn > 0) {
    torn_.fetch_add(torn, std::memory_order_relaxed);
  }
  return n;
}
// [/snippet:snapshot]

TraceCounts FlightRecorder::counts() const noexcept {
  // Summed over the rings rather than kept in one counter: a counter shared by every writer
  // would cost each record a contended read-modify-write (bm_flight_recorder, 4 threads).
  std::uint64_t recorded = 0;
  for (const auto& ring : rings_) {
    recorded += ring.next.load(std::memory_order_relaxed);
  }
  return TraceCounts{recorded, dropped_.load(std::memory_order_relaxed), torn_.load(std::memory_order_relaxed)};
}

void FlightRecorder::clear_for_test() noexcept {
  for (auto& ring : rings_) {
    for (auto& s : ring.slots) {
      s.seq.store(0, std::memory_order_relaxed);
    }
    ring.next.store(0, std::memory_order_relaxed);
  }
  dropped_.store(0, std::memory_order_relaxed);
  torn_.store(0, std::memory_order_relaxed);
}

namespace {
// Constant-initialized, so there is no guard to take on first use: a signal handler may be the
// first to call flight_recorder().
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables): the one process-wide recorder
constinit FlightRecorder process_recorder;
}  // namespace

FlightRecorder& flight_recorder() noexcept { return process_recorder; }

}  // namespace minidaq
