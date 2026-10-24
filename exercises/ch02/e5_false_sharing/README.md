# Exercise 2.5 (M, extra): Per-stage counters without false sharing

**Goal.** Each pipeline stage (decode, sort, pair, write) runs on its own thread and
increments its own statistics counters (events in, events out, drops). `StageCounters`
in the starter packs all four stages' counters next to each other. Lay them out so that
no two stages share a cache line, without changing the public interface, and measure the
effect with the benchmark.

**Time.** 45 minutes.

**Acceptance tests.**
- Counters of different stages are at least 64 bytes apart (`tests/test_counters.cpp` checks
  the addresses).
- Four threads incrementing their own stage concurrently produce exact totals.
- Run `ch02_e5_false_sharing_solution_bench` (Release) and record the speedup in your log.
