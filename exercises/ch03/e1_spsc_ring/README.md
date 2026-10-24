# Exercise 3.1 (M): An SPSC ring for singles

**Goal.** Implement `ex::SinglesRing`, a bounded single-producer single-consumer ring
buffer of `minidaq::Single`, without locks, and measure it between two pinned threads.

**Time.** 2 to 3 hours.

**Starter.** `starter/ring.hpp` has the interface and TODOs. Do not look at
`minidaq/include/minidaq/pipeline/spsc_ring.hpp` until you have a working version: the point
is to make the memory-ordering decisions yourself and then compare.

**Acceptance tests** (`tests/test_ring.cpp`):
- FIFO order, `try_push` fails on a full ring and `try_pop` fails on an empty one.
- Capacity is rounded up to a power of two; indices wrap correctly over many laps.
- `try_push_n` / `try_pop_n` move as many elements as fit and report how many.
- A two-thread stress test moves 2 million singles and checks every one arrives once and in
  order. Run it under ThreadSanitizer too: `ctest --preset tsan -R ch03/e1`.

**Performance target.** At least 50 M singles per second between two pinned threads, measured
with `bench_ring.cpp` (built when benchmarks are on):

    cmake --preset release -DMINIDAQ_BUILD_STARTERS=ON && cmake --build --preset release
    build/release/exercises/ch03/ch03_e1_spsc_ring_starter_bench --benchmark_repetitions=5

On a shared VM, per-item numbers vary a lot between runs (the book shows a 40 to 64 M/s range
for the library ring). Report the median and the spread, and the machine, compiler and flags.
The batched functions should clear the target comfortably.
