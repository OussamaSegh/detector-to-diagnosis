# Exercise 20.4: notes on the solution

**Results** (200 simulated jobs each, noise 1% per run, threshold 5%, alpha 0.01):

| Order and test | No change, drift -2%/run | 10% slower, drift +2%/run |
|---|---|---|
| A then B, 10 rounds, Mann-Whitney | 100% false alarms | 0% found |
| Interleaved, 10 rounds, Mann-Whitney | 0% false alarms | 0.5% found |
| Interleaved, 10 rounds, paired sign test | 0% false alarms | 100% found |
| Interleaved, 5 rounds, paired sign test | 0% | 0%: the smallest p-value is 1/32 |

Running all of A and then all of B turns the drift into the result: a machine that slows down
makes B look slower, one that speeds up hides a real regression. Interleaving removes the bias,
because both sides see the same machine on average, but not the variance: the drift spreads each
side's runs over 20%, and a rank test of two such wide samples cannot see 10%. The ratio of two
neighboring runs cancels the drift, so a test on the rounds' ratios sees the regression clearly;
but a sign test of n rounds cannot reach a p-value below 2^-n, so five rounds can never reject at
0.01. Without drift and with 3% noise the unpaired test is the stronger one (89% against 62% for
a 7% slowdown, 10 rounds): pairing pays only when the machine moves.

**For `tools/perf_ab.sh`.** Its interleaving is right; its unpaired gate is right on a machine
that is noisy but steady, and weak on one that drifts. The first change is to keep the rounds:
record which repetitions belong to which round and add a paired decision with at least 10
rounds, then measure on the runners which of the two finds a planted slowdown more often at the
same false alarm rate. The A/A runs of Chapter 20 are the start of that measurement.
