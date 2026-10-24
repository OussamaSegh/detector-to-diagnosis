# Exercise 5.5 (E, extra): Prove a speedup is real

**Goal.** "It got 8% faster" is a claim about two noisy distributions. Compute a confidence
interval for the speedup from repeated benchmark runs, so that you can tell a real
improvement from a lucky run, and so that your merge request can say "1.06 to 1.11 times
faster (95%)" instead of "8% faster".

**Time.** 60 minutes.

**Tasks.**
1. `ex::speedup_ci(before, after, confidence, resamples, seed)`: the estimate is
   `median(before) / median(after)` (run times, lower is faster). The interval is a percentile
   bootstrap: resample each side with replacement to its own size, recompute the ratio of
   medians `resamples` times, and return the `(1 - confidence) / 2` and
   `1 - (1 - confidence) / 2` percentiles.
2. Reject fewer than 3 samples per side, non-positive or non-finite times, a confidence outside
   (0, 1) and fewer than 100 resamples with `std::invalid_argument`.
3. Use it on two of your own benchmark runs (for example Exercise 5.1's branchy and branchless
   kernels at 50%), from `--benchmark_repetitions=10 --benchmark_format=json`.

**Acceptance tests** (`tests/test_speedup.cpp`): a clear 2x speedup has a tight interval above
1.85; no change gives an interval containing 1; a noisy 5% change with 5 repetitions is not
proven; results are deterministic for a seed; higher confidence gives a wider interval; bad
input is rejected.

**Think about it:** the percentile bootstrap is a good default but is known to be inaccurate
for very small samples. Why are 5 repetitions the minimum this book uses, and what would you
do for a decision that matters (a release gate, a claim in a design review)?
