// SPDX-License-Identifier: MIT
// minidaq_jitter: a small cyclictest-style probe (Chapter 4). One thread
// sleeps until absolute deadlines every --interval-us and records how late it
// woke up. Optional pinning and SCHED_FIFO. Prints percentiles.
//
//   minidaq_jitter --seconds 30 --interval-us 200 --cpu 1 --fifo 80 --mlock
//   minidaq_jitter --seconds 30 --interval-us 200 --cpu 1 --slack-ns 1
#include <cstdio>
#include <ctime>
#include <string_view>

#include "minidaq/core/parse_number.hpp"
#include "minidaq/metrics/latency_histogram.hpp"
#include "minidaq/rt/realtime.hpp"

namespace {

struct Options {
  double seconds = 10.0;
  long interval_us = 1000;
  int cpu = -1;
  int fifo_priority = 0;
  bool mlock = false;
  long slack_ns = -1;  // -1: leave the default
};

bool parse(int argc, char** argv, Options& o) {
  for (int i = 1; i < argc; ++i) {
    const std::string_view a{argv[i]};
    const std::string_view v = i + 1 < argc ? argv[i + 1] : "";
    bool ok = true;
    if (a == "--mlock") {
      o.mlock = true;
    } else if (a == "--seconds") {
      ok = minidaq::parse_into(v, o.seconds, 1e-3, 86400.0);
      ++i;
    } else if (a == "--interval-us") {
      ok = minidaq::parse_into(v, o.interval_us, 1L, 1'000'000L);
      ++i;
    } else if (a == "--cpu") {
      ok = minidaq::parse_into(v, o.cpu, 0, 4095);
      ++i;
    } else if (a == "--slack-ns") {
      ok = minidaq::parse_into(v, o.slack_ns, 1L, 1'000'000'000L);
      ++i;
    } else if (a == "--fifo") {
      ok = minidaq::parse_into(v, o.fifo_priority, 1, 99);
      ++i;
    } else {
      ok = false;
    }
    if (!ok) {
      std::fprintf(stderr, "usage: %s [--seconds S] [--interval-us N] [--cpu C] [--fifo PRIO] [--slack-ns N] [--mlock]\n", argv[0]);
      return false;
    }
  }
  return true;
}

std::int64_t to_ns(const timespec& t) { return std::int64_t{t.tv_sec} * 1'000'000'000 + t.tv_nsec; }

}  // namespace

int main(int argc, char** argv) {
  Options o;
  if (!parse(argc, argv, o)) {
    return 2;
  }
  namespace rt = minidaq::rt;
  if (o.mlock) {
    if (auto r = rt::lock_all_memory(); !r) {
      std::fprintf(stderr, "mlockall: %s\n", r.error().message().c_str());
    }
  }
  const auto st = rt::apply_stage(
      {o.cpu, o.fifo_priority > 0 ? rt::SchedPolicy::fifo : rt::SchedPolicy::other, o.fifo_priority},
      std::size_t{256} * 1024);
  if (st.error) {
    std::fprintf(stderr, "real-time settings: %s\n", st.error.message().c_str());
  }
  if (o.slack_ns >= 0) {
    if (auto r = rt::set_timer_slack_ns(static_cast<unsigned long>(o.slack_ns)); !r) {
      std::fprintf(stderr, "timer slack: %s\n", r.error().message().c_str());
    }
  }
  minidaq::LatencyHistogram h;
  // [snippet:loop]
  const std::int64_t interval_ns = o.interval_us * 1000;
  const auto loops = static_cast<std::int64_t>(o.seconds * 1e9) / interval_ns;
  timespec next{};
  clock_gettime(CLOCK_MONOTONIC, &next);
  for (std::int64_t i = 0; i < loops; ++i) {
    const std::int64_t deadline = to_ns(next) + interval_ns;
    next.tv_sec = static_cast<time_t>(deadline / 1'000'000'000);
    next.tv_nsec = static_cast<long>(deadline % 1'000'000'000);
    // Absolute deadline: an oversleep in one cycle does not shift later ones.
    while (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, nullptr) != 0) {
    }
    timespec now{};
    clock_gettime(CLOCK_MONOTONIC, &now);
    h.record(to_ns(now) - deadline);  // how late we woke up
  }
  // [/snippet:loop]
  const auto s = h.summary();
  std::printf("samples %llu  cpu %d  policy %s  wake-up latency (us): min %.1f  p50 %.1f  p99 %.1f  p99.9 %.1f  p99.99 %.1f  max %.1f\n",
              static_cast<unsigned long long>(s.count), st.running_cpu,
              o.fifo_priority > 0 && st.scheduled ? "fifo" : "other", static_cast<double>(s.min) / 1e3,
              static_cast<double>(s.p50) / 1e3, static_cast<double>(s.p99) / 1e3, static_cast<double>(s.p999) / 1e3,
              static_cast<double>(s.p9999) / 1e3, static_cast<double>(s.max) / 1e3);
  return 0;
}
