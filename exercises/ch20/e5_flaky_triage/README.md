# Exercise 20.5 (M): How sure is "not flaky"?

**Goal.** Put numbers on the decisions a team makes about a test that fails now and then: how
often it fails, how many clean reruns it takes to say it fails less than 1% of the time, whether
a change made it worse, and what a CI rule of "retry a failed test twice" hides. MiniDAQ's own
history has the cases: MDQ-PR-019 failed 8 of 8 runs under load before its correction and 0 of 8
after, and MDQ-PR-020 passed every run on one machine and failed every run on another.

**Time.** 60 minutes.

**Starter.** `starter/flaky.py`, with the binomial distribution given.

**Tasks.**
1. `failure_rate_interval(failures, runs, confidence)`: the exact (Clopper-Pearson) two-sided
   interval of the failure rate. Find each end by bisection on the binomial distribution.
2. `runs_needed(max_rate, confidence)`: the number of reruns without a failure after which the
   one-sided upper bound of the failure rate is below `max_rate`.
3. `worse_after(fail_before, runs_before, fail_after, runs_after)`: the one-sided p-value of
   Fisher's exact test that the failure rate after a change is higher than before.
4. `retries_hide(rate, retries)`: the probability that a test which fails with probability
   `rate` on each run is reported as passed under a rule that retries a failure `retries` times.

**Acceptance** (`ch20/e5_flaky_triage/<variant>/unittest`): hand-computed intervals of 0 of 10 and
8 of 8; 299 reruns for "below 1% with 95% confidence"; the MDQ-PR-019 comparison; the hiding
probability of two retries; consistency between the functions.

Then answer in `NOTES.md`: CAPA-0001 forbids fixed sleeps in tests and Chapter 20 forbids
automatic retries. With your numbers, explain to a colleague who wants "just one retry" what it
would have done to MDQ-PR-019, and what you propose instead.
