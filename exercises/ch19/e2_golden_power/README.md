# Exercise 19.2 (M): What the golden comparison can see

**Goal.** Find out how large a change of a rate MiniDAQ's statistical comparison with golden data
detects, and check the answer by simulation. A comparison that passes says the difference was not
larger than chance makes likely; it does not say there was none. Before you trust a pass, you
need the smallest difference the test finds with a stated probability, its power.

**Time.** 90 minutes.

**Starter.** `starter/power.py`. The comparison under study is `stats.poisson_rates_equal` in
`minidaq/tests/system/stats.py` (two Poisson counts in equal times); the tests put that directory
on the path, so `import stats` works. A Poisson sampler, `poisson()`, is given.

**Tasks.**
1. `min_detectable_ratio(n, alpha, power)`: the smallest ratio `r > 1` of the new run's rate to
   the golden run's that the comparison finds with probability `power`, when the golden run
   counted `n`. Use the normal approximation: the difference of the counts is about `n (r - 1)`
   with a standard deviation of about `sqrt(n (1 + r))`, and solve for `r`. Refuse nonsense.
2. `simulated_power(n, ratio, alpha, trials, seed)`: the fraction of simulated pairs of runs that
   the comparison rejects.
3. `report(golden)`: for the prompts and the delayed coincidences of a golden file, the smallest
   rate change in percent that its comparison finds with 90% power at the significance level of
   the system test plan (`0.001`).

**Acceptance** (`ch19/e2_golden_power/<variant>/unittest`): a hand-computed case; power and count
move the answer the right way; without a difference the test fails at about `alpha`; the formula
agrees with the simulation within 3 percentage points of power; the exact test is conservative at
small counts; the report of `minidaq/tests/system/golden/seed1.json`.

Then answer in `NOTES.md`: what does the report say about the delayed comparison of the golden
run, and what would you change in the test (not in the threshold) to make it see a 5% change of
the randoms rate?
