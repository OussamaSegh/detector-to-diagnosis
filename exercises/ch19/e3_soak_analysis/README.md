# Exercise 19.3 (M): Reading a soak test

**Goal.** Turn the samples of a soak test into a verdict: memory that keeps growing, latency that
drifts, a counter that wraps, a stall, a loss or a fault. `tools/soak.py` checks memory, losses and
faults; your analysis checks everything a long run can show, and must not fail a run on noise.

**Time.** 90 minutes.

**Starter.** `starter/soak_analysis.py`: `load_csv()` reads the `samples.csv` that
`tools/soak.py` writes; `analyze()` checks only for loss. The kinds of problem and their meaning
are in the module's comment.

**Tasks.**
1. `slope(xs, ys)`: the least-squares slope and its standard error.
2. `analyze(rows, ...)`: after the warm-up, memory and p99 latency trends that exceed their limit
   by two standard errors; a counter that goes down; an interval whose input rate falls below
   `min_rate_fraction` of the median; a loss; a fault or a state other than `running` before the
   last sample; and a run too short to judge.

**Acceptance** (`ch19/e3_soak_analysis/<variant>/unittest`): a steady run passes for five seeds; a
leak of 3 MiB/h is found and growth during the warm-up is not; noise of half a MiB per sample is
not a leak; latency drift, a wrapped counter, one stalled interval, a loss and a fault are each
found and named; a short run cannot pass; a CSV in `soak.py`'s format loads with its types.

Then answer in `NOTES.md`: a run allocates a 2 MiB buffer once, 15 minutes in, and never again.
What does your analysis say, and is that the right verdict? What would tell a step from a leak?
