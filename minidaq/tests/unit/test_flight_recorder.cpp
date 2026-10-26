// SPDX-License-Identifier: MIT
#include <gtest/gtest.h>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <latch>
#include <thread>
#include <vector>

#include "minidaq/core/flight_recorder.hpp"

using namespace minidaq;

namespace {

// Each test records from threads of its own, so that the rings are given back when the threads
// exit and the main thread holds none. The recorder is large (about 330 KB), so it is static.
FlightRecorder& fresh() {
  static FlightRecorder r;
  r.clear_for_test();
  return r;
}

void in_thread(auto f) { std::thread{f}.join(); }

std::vector<TraceEvent> snapshot(FlightRecorder& r, std::size_t n = FlightRecorder::kCapacity) {
  std::vector<TraceEvent> out(n);
  out.resize(r.snapshot_into(out));
  return out;
}

}  // namespace

TEST(FlightRecorder, KeepsAThreadsEventsInTheOrderItRecordedThem) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  in_thread([&] {
    for (std::uint64_t i = 0; i < 10; ++i) {
      r.record(TraceCode::note, i, 100 + i);
    }
  });
  const auto events = snapshot(r);
  ASSERT_EQ(events.size(), 10U);
  for (std::uint64_t i = 0; i < 10; ++i) {
    EXPECT_EQ(events[i].code, TraceCode::note);
    EXPECT_EQ(events[i].seq, i + 1);
    EXPECT_EQ(events[i].a, i);
    EXPECT_EQ(events[i].b, 100 + i);
    if (i > 0) {
      EXPECT_GE(events[i].t_ns, events[i - 1].t_ns);
    }
  }
  EXPECT_EQ(r.counts().recorded, 10U);
  EXPECT_EQ(r.counts().dropped, 0U);
}

TEST(FlightRecorder, KeepsTheLastEventsOfARingWhenItWrapsAround) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  in_thread([&] {
    for (std::uint64_t i = 0; i < 1000; ++i) {
      r.record(TraceCode::note, i);
    }
  });
  const auto events = snapshot(r);
  ASSERT_EQ(events.size(), FlightRecorder::kRingEvents);
  EXPECT_EQ(events.front().a, 1000 - FlightRecorder::kRingEvents);
  EXPECT_EQ(events.back().a, 999U);
  EXPECT_EQ(events.back().seq, 1000U);
  EXPECT_EQ(r.counts().recorded, 1000U);
}

TEST(FlightRecorder, ASmallSnapshotKeepsTheNewestEventsOldestFirst) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  in_thread([&] {
    for (std::uint64_t i = 0; i < 100; ++i) {
      r.record(TraceCode::note, i);
    }
  });
  const auto events = snapshot(r, 8);
  ASSERT_EQ(events.size(), 8U);
  for (std::uint64_t i = 0; i < 8; ++i) {
    EXPECT_EQ(events[i].a, 92 + i);
  }
}

TEST(FlightRecorder, MergesTheRingsOfSeveralThreadsByTime) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  // One thread after the other, so that the times interleave in a known way.
  for (std::uint64_t t = 0; t < 3; ++t) {
    in_thread([&] { r.record(TraceCode::note, t); });
  }
  const auto events = snapshot(r);
  ASSERT_EQ(events.size(), 3U);
  for (std::uint64_t t = 0; t < 3; ++t) {
    EXPECT_EQ(events[t].a, t);
  }
}

TEST(FlightRecorder, AThreadGivesItsRingBackWhenItExits) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  // More threads than rings, one at a time: each finds the ring of the one before free.
  for (std::size_t t = 0; t < 2 * FlightRecorder::kRings; ++t) {
    in_thread([&] { r.record(TraceCode::note, t); });
  }
  EXPECT_EQ(r.counts().recorded, 2 * FlightRecorder::kRings);
  EXPECT_EQ(r.counts().dropped, 0U);
}

TEST(FlightRecorder, CountsTheEventsOfThreadsThatFindNoFreeRing) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  constexpr std::size_t kThreads = FlightRecorder::kRings + 3;
  std::latch recorded{static_cast<std::ptrdiff_t>(kThreads)};
  std::vector<std::thread> threads;
  for (std::size_t t = 0; t < kThreads; ++t) {
    threads.emplace_back([&] {
      r.record(TraceCode::note, 1);
      r.record(TraceCode::note, 2);
      recorded.arrive_and_wait();  // every thread holds its ring (or none) until all recorded
    });
  }
  for (auto& t : threads) {
    t.join();
  }
  EXPECT_EQ(r.counts().recorded, 2 * FlightRecorder::kRings);
  EXPECT_EQ(r.counts().dropped, 2 * (kThreads - FlightRecorder::kRings));
}

TEST(FlightRecorder, ASnapshotTakenWhileThreadsRecordNeverShowsHalfAnEvent) {
  // REQ: SRS-DIAG-001
  auto& r = fresh();
  constexpr int kWriters = 4;
  std::atomic<bool> stop{false};
  std::vector<std::thread> writers;
  for (int w = 0; w < kWriters; ++w) {
    writers.emplace_back([&] {
      for (std::uint64_t i = 1; !stop.load(std::memory_order_relaxed); ++i) {
        r.record(TraceCode::note, i, ~i);  // b is always the complement of a
      }
    });
  }
  std::vector<TraceEvent> out(FlightRecorder::kCapacity);
  std::size_t seen = 0;
  for (int k = 0; k < 200; ++k) {
    const std::size_t n = r.snapshot_into(out);
    for (std::size_t i = 0; i < n; ++i) {
      ASSERT_EQ(out[i].b, ~out[i].a) << "a torn event in snapshot " << k;
      ASSERT_EQ(out[i].code, TraceCode::note);
      if (i > 0) {
        ASSERT_LE(out[i - 1].t_ns, out[i].t_ns);
      }
    }
    seen += n;
  }
  stop.store(true);
  for (auto& t : writers) {
    t.join();
  }
  EXPECT_GT(seen, 0U);
  // The torn count is whatever the race gave; it only has to be plausible.
  EXPECT_LE(r.counts().torn, 200U * FlightRecorder::kCapacity);
}

TEST(FlightRecorder, TheProcessRecorderIsOneObject) {
  // REQ: SRS-DIAG-001
  EXPECT_EQ(&flight_recorder(), &flight_recorder());
  const auto before = flight_recorder().counts().recorded;
  in_thread([] { trace(TraceCode::note, 7); });
  EXPECT_EQ(flight_recorder().counts().recorded, before + 1);
}

TEST(FlightRecorder, NamesEveryCode) {
  EXPECT_EQ(to_string(TraceCode::state), "state");
  EXPECT_EQ(to_string(TraceCode::command), "command");
  EXPECT_EQ(to_string(TraceCode::run_begin), "run_begin");
  EXPECT_EQ(to_string(TraceCode::run_end), "run_end");
  EXPECT_EQ(to_string(TraceCode::link_gap), "link_gap");
  EXPECT_EQ(to_string(TraceCode::fault), "fault");
  EXPECT_EQ(to_string(TraceCode::link_resync), "link_resync");
  EXPECT_EQ(to_string(TraceCode::note), "note");
  EXPECT_EQ(to_string(TraceCode::none), "none");
}
