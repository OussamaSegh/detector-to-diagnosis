// SPDX-License-Identifier: MIT
// MiniDAQ - the flight recorder: the last events of every thread, kept in memory (Chapter 21).
//
// A log written to a file tells you what happened if you were writing the right things at the
// right level when it happened. The flight recorder keeps the last events of each thread in a
// fixed ring in memory instead, always on, so that after a fault, a crash or a puzzling rate
// you can ask the running server what it did last (control command "diagnostics") or read it
// from the crash report, without restarting it with more logging.
//
// Design (after the per-CPU ring buffers of Linux ftrace and LTTng):
//  - each thread that records claims one ring of kRingEvents events on its first record and
//    gives it back when it exits; a ring has exactly one writer at a time, so a write is a few
//    relaxed stores and two release stores, without a compare-and-swap and without a lock;
//  - each event slot has a sequence number that is odd while the slot is written (a seqlock):
//    a reader copies the slot and keeps it only if the number was even and unchanged, so a
//    snapshot never shows half of an event, even when it is taken while the thread writes;
//  - everything is a lock-free atomic and the memory is static, so snapshot_into() is
//    async-signal-safe and the crash handler can call it (minidaq/rt/crash_report.hpp);
//  - when all rings are taken, a new thread's events are counted as dropped, not recorded.
// Writers never wait for readers and readers never stop writers: recording costs a writer
// about the same whether or not someone is reading (bm_flight_recorder).
#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace minidaq {

// What happened. The meaning of the two arguments a and b depends on the code.
enum class TraceCode : std::uint8_t {
  none = 0,
  state = 1,        // the acquisition state changed: a = from, b = to (AcqState values)
  command = 2,      // a control command was handled: a = CommandId, b = 1 if it succeeded
  run_begin = 3,    // a run started: a = run number
  run_end = 4,      // a run's data is durable: a = run number, b = 1 if complete, 0 if losses
  link_gap = 5,     // the readout link declared packets lost: a = lost now, b = lost in total
  fault = 6,        // the run failed: a = run number, b = FaultSource
  link_resync = 7,  // the readout link's numbering jumped: a = resynchronizations in total
  note = 8,         // anything else: a and b free
};

[[nodiscard]] std::string_view to_string(TraceCode c) noexcept;

// The commands that TraceCode::command records, as numbers (the event holds no strings).
enum class CommandId : std::uint8_t { other = 0, configure, start, stop, reset, status, diagnostics, auth };

// Where the fault of TraceCode::fault came from.
enum class FaultSource : std::uint8_t { other = 0, detector, sink, sorter };

struct TraceEvent {
  std::uint64_t seq = 0;    // the event's number in its ring, from 1
  std::uint64_t t_ns = 0;   // CLOCK_MONOTONIC, nanoseconds
  std::uint32_t ring = 0;   // which ring (one per thread at a time)
  TraceCode code = TraceCode::none;
  std::uint64_t a = 0;
  std::uint64_t b = 0;
};

struct TraceCounts {
  std::uint64_t recorded = 0;  // events written since the start of the process
  std::uint64_t dropped = 0;   // events of threads that found no free ring
  std::uint64_t torn = 0;      // events a snapshot skipped because a writer overwrote them
};

class FlightRecorder {
 public:
  static constexpr std::size_t kRings = 32;
  static constexpr std::size_t kRingEvents = 256;  // a power of two
  static constexpr std::size_t kCapacity = kRings * kRingEvents;

  FlightRecorder() = default;
  FlightRecorder(const FlightRecorder&) = delete;
  FlightRecorder& operator=(const FlightRecorder&) = delete;
  FlightRecorder(FlightRecorder&&) = delete;
  FlightRecorder& operator=(FlightRecorder&&) = delete;
  ~FlightRecorder() = default;

  // Records one event for the calling thread. Wait-free; never allocates.
  void record(TraceCode code, std::uint64_t a = 0, std::uint64_t b = 0) noexcept;

  // Copies the newest events of all rings into `out`, oldest first by time, and returns how
  // many it copied (at most out.size()). Async-signal-safe: no allocation, no lock. Events a
  // writer overwrites during the copy are skipped and counted as torn.
  std::size_t snapshot_into(std::span<TraceEvent> out) noexcept;

  [[nodiscard]] TraceCounts counts() const noexcept;

  // For tests: forget every event. Only while no thread records.
  void clear_for_test() noexcept;

 private:
  struct Slot {
    std::atomic<std::uint64_t> seq{0};  // 2n+1 while event n is written, 2n+2 when it is complete
    std::atomic<std::uint64_t> t_ns{0};
    std::atomic<std::uint64_t> a{0};
    std::atomic<std::uint64_t> b{0};
    std::atomic<std::uint8_t> code{0};
  };
  // A cache line of its own for each ring, so that writers of neighboring rings do not share one.
  struct alignas(64) Ring {
    std::atomic<bool> owned{false};
    std::atomic<std::uint64_t> next{0};  // events written to this ring, ever
    std::array<Slot, kRingEvents> slots{};
  };
  friend struct RingLease;
  Ring* claim() noexcept;
  // Copies event n of `ring` into e; false if a writer overwrote it during the copy.
  static bool read_slot(const Ring& ring, std::uint64_t n, TraceEvent& e) noexcept;

  std::array<Ring, kRings> rings_{};
  std::atomic<std::uint64_t> dropped_{0};
  std::atomic<std::uint64_t> torn_{0};
};

// The process's recorder. MiniDAQ's code records into it; tests may make their own.
FlightRecorder& flight_recorder() noexcept;

// Shorthand for flight_recorder().record(...).
inline void trace(TraceCode code, std::uint64_t a = 0, std::uint64_t b = 0) noexcept {
  flight_recorder().record(code, a, b);
}

}  // namespace minidaq
