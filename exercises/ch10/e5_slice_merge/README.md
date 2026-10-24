# Exercise 10.5 (M): Merge by time slices, and measure it against the heap

**Goal.** MiniDAQ's `StreamMerger` merges board streams with a heap: one heap operation
per single. Write the other common design, merging by time slices: take every board's
singles of the slice [T, T + Δ), sort them together, emit, move on. Make its output
identical to the heap merger's, ties included, then measure which is faster for 4, 24
and 72 boards and say what each design costs in latency.

**Time.** 2 hours.

**Starter.** `starter/slice_merge.cpp` includes a single that sits exactly on a slice edge in
two slices, stops before the last partial slice, and sorts with `std::sort`, which does not
keep the boards' order for equal singles.

**Acceptance** (`tests/test_slice_merge.cpp`):
- For 1, 4, 24 and 72 boards and slices from 1 ns to 10 us, on streams where ties across
  boards and singles on slice edges are common: exactly the heap merger's output.
- Singles on the edges, an empty board, and a last single alone in its slice.

**Measure.** `solution/bench_slice_merge.cpp` (built as
`build/release/exercises/ch10/ch10_e5_slice_merge_solution_bench`) compares the two on
0.1 s of simulated 20 MBq data split by block. Run it with `--benchmark_repetitions=5` and
report the medians.

**Hints.** Half-open intervals make "exactly one slice per single" automatic. Which sort
keeps equal elements in the order you gathered them, and in what order must you gather
them?
