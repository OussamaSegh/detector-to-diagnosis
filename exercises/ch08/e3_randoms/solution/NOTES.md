# Exercise 8.3: notes on the solution

**Derivation.** Detector 1 delivers S1 singles per second. Each one makes a random pair
with any single of detector 2 that falls in the interval [t - tau, t + tau], of length
2 tau. Detector 2's singles are a Poisson process independent of detector 1, so that
interval holds S2 * 2 tau of them on average. Hence R = S1 * 2 tau * S2 = 2 tau S1 S2,
valid while 2 tau S2 is much less than 1 (otherwise pairs overlap into multiples).

**The estimate.** 2 * 4 ns * 1e6 /s * 1e6 /s = 8,000 randoms per second. With true
coincidences between the same two detectors at, say, 10,000 per second, almost half
of the prompts would be randoms: the window is the first lever on that number, the
activity the second (R grows with its square, trues linearly).

**The measurement.** The test counts about 8,000 pairs in 1 s of two 1 M/s streams. The
starter counted only pairs where the single in `b` comes after the one in `a`, half
the window, and got about 4,000; its formula had the same factor 2 missing, so the two
agreed with each other and both were wrong. Check a formula against an independent
measurement, not against code written with the same assumption.

**The counter.** Two pointers that only move forward give O(n + m). The starter's
inner loop restarted at `j` for every single in `a`, which is correct but quadratic
in the number of pairs per window; with 4 ns windows and 1 M/s that is harmless, at
higher rates or wider windows it is not.
