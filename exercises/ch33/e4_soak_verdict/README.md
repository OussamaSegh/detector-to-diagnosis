# Exercise 33.4 (M): What a soak's intervals above the limit show

**Goal.** ACC-04 accepts a soak of 180 intervals with at most one above the latency limit. Find
out what that shows about the fraction of intervals above the limit on the machine, with exact
binomial bounds, how long a soak would have to be to show at most 1%, and give a verdict that
says when a soak was too short to tell.

**Time.** 1 hour.

**Starter.** `starter/exceed.py`, with `upper_bound(k, n, confidence)`, `lower_bound(k, n,
confidence)`, `intervals_needed(p_max, confidence, allowed)` and `verdict(k, n, p_max,
confidence)`. It uses the normal approximation `k/n ± z sqrt(p(1-p)/n)`, and its verdict is
DEMONSTRATED or EXCEEDED by `k/n` alone.

**Acceptance** (`tests/test_exceed.py`, run by `ctest --test-dir build/debug -R ch33/e4`):
- With none above, the upper bound is `1 - (1 - c)^(1/n)` for every n and confidence.
- Over every possible soak of 180 intervals, the upper bound falls below a true fraction of 0.3%,
  1% or 3% with a probability of at most 5%, and the lower bound above 1% or 5% likewise.
- 900 above out of 100,000 gives bounds around 0.9% without overflowing.
- Impossible counts, and a confidence of 1, raise `ValueError`.
- 299 intervals with none above show 1% at 95%; 473 with one above; 459 with none at 99%.
- Verdicts: 0 or 1 of 180, 5 of 1,000 and 0 of 1 are INCONCLUSIVE; 15 of 180 and 20 of 1,000
  EXCEEDED; 0 of 300 DEMONSTRATED.

**Then, by hand.**
1. What upper bound did the starter give for 0 of 180, and how often does its bound miss a true
   fraction of 1%? Why is the normal approximation worst exactly where a soak lives?
2. If the machine's true fraction were 1%, how often would a soak of 180 pass ACC-04? And at 3%?
   What does ACC-04 show, then, and what does it not?
3. The bounds assume that intervals are independent. Name what makes neighboring intervals of
   the soak alike, and say what it does to the bounds.

**Hints.** `P(X <= k)` for a binomial is a sum of `C(n, i) p^i (1-p)^(n-i)`; in log space with
`math.lgamma` it does not overflow. It decreases with p, so the bound is found by bisection.
