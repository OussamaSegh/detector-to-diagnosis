# Exercise 31.4 (M): The mean and spread of each crystal over a run read in chunks

**Goal.** A QC pass over a long run reads it block by block and never holds it whole. Keep, per
crystal, the count, the mean and the variance of a value (a time difference, an energy, a time
stamp) in one pass, in memory that does not grow with the run, and get the same numbers as two
passes over everything in memory: whatever the chunk sizes, with crystals missing from a chunk, and
with values that share a large offset.

**Time.** 1.5 hours.

**Starter.** `starter/running.py`. `RunningStats(crystals)` has `add(crystal, values)`, the
attributes `n` and `mean`, and `variance()`. It averages the chunks' means without weighting them,
keeps the sum of squares and computes the variance as `(sum2 - n mean^2) / (n - 1)`, and checks
nothing.

**Acceptance** (`tests/test_running.py`, run by `ctest --test-dir build/debug -R ch31/e4`):
- On 200,000 values of 64 crystals read in equal chunks, the counts equal `np.bincount`, the means
  agree with a two-pass reference within 1e-9 and the variances within a relative 1e-9.
- The same with unequal chunks (1,000 values of crystal 0 only, then 7, 0, 150,000 and 3).
- With every value offset by 3.6e15 (time stamps in picoseconds, an hour into a run, spread 50 ps),
  the variances agree within a relative 1e-6.
- A crystal with fewer than two values has the variance NaN; one with a single value has that
  value as its mean.
- A crystal id outside the range raises `IndexError`; arrays of different shapes raise
  `ValueError`.

**Then, by hand.**
1. Why does the mean of the chunks' means pass the first test almost, and fail the second by
   hundreds? When would it be exact?
2. What variance did `sum2 - n mean^2` give at the offset 3.6e15? How many significant digits does
   a double have, and how many does `x^2` for `x = 3.6e15` need to resolve a spread of 50?
3. Your merge subtracts the means of two chunks. Does that alone make the offset harmless? What
   does, and what is the cost?

**Hints.** Two summaries `(na, mean_a, M2_a)` and `(nb, mean_b, M2_b)`, where `M2` is the sum of
squared deviations from the mean, merge exactly: `n = na + nb`, `d = mean_b - mean_a`,
`mean = mean_a + d nb / n`, `M2 = M2_a + M2_b + d^2 na nb / n`. `np.bincount(crystal, weights,
minlength=k)` sums per crystal without a Python loop. Keep everything relative to a per-crystal
origin.
