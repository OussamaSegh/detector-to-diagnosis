# Exercise 5.1 (M): Three energy-window filters on 100 M singles

**Goal.** Implement the same energy window filter three ways (with a branch, without a branch,
and with SIMD), prove they compute the same result, and measure them on 100 million singles
with data that defeats and data that helps the branch predictor. Then explain every number.

**Time.** 3 hours.

**Tasks.**
1. In `filters.cpp`, implement `ex::filter_branchy`, `ex::filter_branchless` and
   `ex::filter_simd`. Each copies the singles of `in` whose energy is in `[lo, hi]` (inclusive;
   NaN is rejected) to the front of `out`, in order, and returns how many. `out.size()` is at
   least `in.size()`.
2. For `filter_simd`, use AVX2 or AVX-512 intrinsics with a `target` attribute and a run-time
   check (`__builtin_cpu_supports`), or `std::experimental::simd`. Fall back to the branchless
   version when the CPU cannot run your kernel, so the tests pass everywhere.
3. Run `bench_filters` (built with the `release` preset, `MINIDAQ_BUILD_STARTERS=ON` for your
   own code) pinned to one CPU: `taskset -c 2 ch05_e1_energy_filters_starter_bench
   --benchmark_repetitions=5`. It filters 100 M singles (1.6 GB; set `EX_SINGLES` for less) at
   10%, 50% and 90% acceptance, with energies in random and in sorted order.
4. In `NOTES.md`, give the table and explain: why the branchy filter's speed depends on the
   acceptance and the order, why SIMD wins less than the 4x or 8x the register width
   suggests, and how many bytes per second each kernel moves compared to your machine's
   memory bandwidth.

**Acceptance tests** (`tests/test_filters.cpp`): all three kernels equal a reference on random
data for every size from 0 to 40, inclusive boundaries, NaN and infinities, and 100,000 random
singles.

**Hint.** Before you trust a benchmark of a branchy loop, ask how many different inputs it
sees. A loop that filters the same 4,096 singles a million times teaches the branch predictor
the answers.
