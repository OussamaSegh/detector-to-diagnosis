# Exercise 33.4: notes on the solution

## 1. The normal approximation

For 0 of 180 the starter's upper bound is 0: `p = 0`, so the width `sqrt(p(1-p)/n)` is 0, and its
`intervals_needed(0.01)` is 1, a single quiet interval. The exact bound is 1.65%. Enumerating
every soak of 180, the starter's bound falls below a true fraction of 1% with a probability of
16.4% instead of at most 5%, and below 0.3% with 58%. The approximation needs many events on both
sides; a soak is built to have almost none above the limit, where the binomial is most skewed and
the approximation is worst. The exact bound misses 1% never (no count of 180 puts it below 1%),
and 3% with 2.7%: Clopper-Pearson is conservative, never optimistic.

## 2. What ACC-04 shows

With a true fraction of 1%, a soak of 180 has at most one interval above with a probability of
46%; with 3%, of 2.7%. So ACC-04 rejects a machine that is clearly worse than 1% and passes one
at 1% only about half the time. One of 180 bounds the fraction at 2.6% (95%), and none of 180 at
1.65%: neither demonstrates 1%. That takes 299 quiet intervals, 50 minutes of soak, or 473 with
one allowed. ACC-04 is a release rule that a regression fails; it is not a statistical
demonstration that the 99th percentile holds in 99% of all intervals, and the acceptance report
should not word it as one. The 0.8.0 soak, 15 of 180, is EXCEEDED: its lower bound is 5.2%.

## 3. Independence

Neighboring intervals share the machine's state: another guest's load (the steal time that the
soak records), the page cache and allocator state after a burst, a CPU frequency step, a
periodic job on the host. Peaks therefore come in runs, as 0.8.0's did. Correlated intervals
carry less information than independent ones: the effective number of intervals is smaller than
180, and the true bounds are wider than the binomial ones. Recording the steal time with each
interval is what lets a reviewer see a run of peaks for what it is; a longer soak, or several
soaks on different days, is what narrows the bounds honestly.
