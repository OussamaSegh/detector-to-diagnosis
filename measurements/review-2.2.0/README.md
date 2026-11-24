# Review of release 2.2.0: the evidence of the deviation checked again

Made on 2026-11-24 by the independent review of release 2.2.0 (MDQ-PR-099), on the same
compiler as the release checks (GCC 13.3.0, preset `release`).

## The benchmark the regression gate judged slower

`measurements/mdq-pr-096/bm_sort_functor.s` holds one build's listing of `BM_SortFunctor`'s own
body, with every immediate replaced by `IMM` and the callees' addresses removed; the sort itself
(`std::__introsort_loop<..., TimeOrder>`) is a separate function it calls, so the listing alone
could not show the sort unchanged. Here `bm_sort` was built from `book-v2.1.0` and from the
candidate 5647d2e in two worktrees, and every function whose name holds `BM_SortFunctor` or
`TimeOrder` was compared with its immediates kept and only addresses and offsets normalized:
3 functions (`BM_SortFunctor`, its `.cold` part and `__introsort_loop`, into which the
insertion sort is inlined), 748 instructions, identical. `bm_sort_functor-and-callees.s` is the
listing; both builds' listings have the SHA-256
`f4750819f1a0b8b7b5851d5af608b74db5cc9055404593b98910cfb422dcabfb`.

The benchmark's input comes from the synthetic source, whose code CR-0037 changed.
`generator_hash.cpp`, linked against each build's libraries, hashes 4,194,304 words of the
source for seeds 1 and 7 and for the default configuration the benchmark uses: the same hash in
both builds (`1ec73ba38aee091f`, `c8531080982f983c`). The sort, its machine code and its input
are those of 2.1.0, so the gate's second verdict is not in the commit.

```sh
objdump -d --no-show-raw-insn -C build/release/benchmarks/bm_sort    # then keep the functions above
g++ -std=c++23 -O2 -Iminidaq/include generator_hash.cpp <the build's libminidaq*.a>
```

## The CPU waits in the soak

Each soak's `samples.csv` (`measurements/mdq-pr-096/`) gives, per interval of 10 s, the 99th
percentile of the latency (`p99_ms`) and the largest wait of one server thread for a CPU in one
second (`runq_wait_1s_max_ms`):

| Soak | Intervals | With a wait of 20 ms or more | Slow (p99 above 10 ms) | Median wait, all | Median wait, slow | Correlation |
|---|---|---|---|---|---|---|
| `first/` (candidate) | 600 | 594 | 8 | 24.0 ms | 40.6 ms | 0.31 |
| `rerun/` (candidate) | 600 | 598 | 11 | 24.4 ms | 29.2 ms | 0.22 |
| `control-2.1.0/` | 600 | 594 | 6 | 25.5 ms | 30.2 ms | 0.23 |

A wait of 20 ms or more is in 99% of all intervals, slow or not, so finding one in every slow
interval does not point to the machine; the longer waits of the slow intervals are a weak
association (correlation 0.2 to 0.3), in the candidate and the control alike, as MDQ-PR-064
found at 2.0.x.

## What the counts show

- Candidate against control, the same machine and evening: 19 slow intervals of 1,200 against
  6 of 600, Fisher's exact test one-sided p = 0.22. No evidence that 2.2.0 is worse than 2.1.0.
- Candidate against the requirement: 19 of 1,200 is 1.58% (95% interval 0.96% to 2.46%,
  Clopper-Pearson). With a true share of 1%, the most SRS-PERF-022 allows, 19 or more would
  happen with probability 0.037. On that machine that day the requirement is not shown met by
  2.2.0, nor by 2.1.0's programs (6 of 600, at the limit).
- Candidate against 2.1.0's two soaks (its release, 3, and the control, 6): 19 of 1,200 against
  9 of 1,200, one-sided p = 0.043. The release soak of 2.1.0 ran on another day, so this mixes
  the machine's state with the code; it is the comparison CR-0038 would make interleaved.
