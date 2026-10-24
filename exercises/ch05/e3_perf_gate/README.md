# Exercise 5.3 (H): A CI job that fails when throughput regresses by more than 5%

**Goal.** A performance regression gate that a merge request cannot pass if it made a
benchmark more than 5% slower, and that does not fail at random when the machine is merely
noisy. Two conditions together: the median got slower by more than the threshold, *and* a
statistical test says the difference is unlikely to be noise.

**Time.** 3 to 4 hours, including the CI job.

**Tasks.**
1. In `perf_gate.py`, `load()` is given: it reads per-repetition samples from Google Benchmark
   JSON (`--benchmark_repetitions=N --benchmark_format=json`), ignoring aggregates, and
   records whether larger is better (items per second) or smaller is better (time).
2. Implement `mann_whitney_p_less(a, b)`: the one-sided, exact Mann-Whitney U test that the
   values in `a` tend to be smaller than those in `b`. Count, do not approximate: with 5 to 20
   repetitions, the normal approximation is poor and the exact distribution is cheap (dynamic
   programming over the number of orderings with each U).
3. Implement `compare(baseline, current, threshold, alpha)`: convert both sides to "speed"
   (larger is better), compute the ratio of medians, and mark a benchmark as regressed if
   `ratio < 1 - threshold` and `p < alpha`. A benchmark missing from the current run, or with
   fewer than 5 repetitions on either side, is reported and not judged; a benchmark whose
   metric changed between runs fails.
4. Implement `main()`: print a table, exit with 1 if anything regressed (or, with `--strict`,
   if a baseline benchmark is missing) and 0 otherwise.
5. Wire it into CI: a job that builds the `release` preset on a dedicated runner, runs the
   benchmarks pinned to one CPU with `--benchmark_repetitions=10`, and runs your gate against
   a committed baseline. The repository's own version is `.github/workflows/perf.yml` with
   `tools/perf_gate.py`; read it after you have written yours.

**Acceptance tests** (`tests/test_perf_gate.py`, run by CTest or by
`PYTHONPATH=starter python3 -m unittest discover -s tests`): only repetitions are loaded and
the metric is recognized; exact p-values for small cases; interleaved samples are not
significant; a clear 10% regression fails; a 3% slowdown passes; a noisy slowdown is not
significant; faster passes; time metrics are inverted correctly; missing benchmarks and too
few repetitions are reported but do not fail; exit status.

**Think about it:** the gate compares against a baseline recorded on the *same* runner. What
goes wrong if the baseline was recorded on a developer's laptop, and how often should the
baseline be re-recorded?
