# Exercise 20.4 (H): A/B on a machine that drifts

**Goal.** Find out what the order of benchmark runs does to a regression gate on a machine whose
speed changes during the job, as a shared CI runner's does (a neighbor starts, the CPU heats up).
Then build the comparison that sees a real regression through the drift.

**Time.** 2 hours.

**Starter.** `starter/ab.py`: a model of the machine (`simulate()`: B is `ratio` times as fast as
A, the machine's speed changes by `drift` per run, each run has a noise), and the alarm rates
over many simulated jobs. The gate of Chapter 5 is `tools/perf_gate.py`; the tests put it on the
path.

**Tasks.**
1. `schedule(rounds, interleave)`: all A then all B, or interleaved A B, B A, A B, ...
2. `decide(a, b)`: the gate of Chapter 5 on speeds: the median ratio below `1 - threshold` and a
   one-sided Mann-Whitney test (`perf_gate.mann_whitney_p_less`) below `alpha`.
3. `round_ratios(order, runs)`: B over A within each round of an interleaved order.
4. `sign_test_p_less(ratios)` and `decide_paired(order, runs)`: the same decision on the rounds'
   ratios, with a sign test.

**Acceptance** (`ch20/e4_ab_drift/<variant>/unittest`): with 2% drift per run, A-then-B raises a
false alarm in at least 90% of jobs and hides a 10% regression in at least 90%; interleaving
removes the false alarm but, unpaired, still misses the regression; paired rounds find it in at
least 95% of jobs with 10 rounds; 5 rounds are too few for the sign test at `alpha = 0.01`.

Then answer in `NOTES.md`: `tools/perf_ab.sh` interleaves but compares unpaired, with 5 rounds of
2 repetitions. What do your results say about it, and what would you change first?
