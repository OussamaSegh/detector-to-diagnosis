# Exercise 38.4 (M): Jitter, wander and the Allan deviation

**Goal.** Chapter 38 tells jitter from wander by the time over which a clock's error varies. The
Allan deviation is the measure that makes the difference a number: from a record of a clock's time
error, the spread of its frequency averaged over a time tau, for every tau. Compute it, check it on
clocks whose answer is known, and see what it does and does not see.

**Time.** 1 hour.

**Starter.** `starter/allan.py`, with `adev(x, tau0, m)`, `curve(x, tau0)` and `slope(points)`.
`x[i]` is the time error at `i * tau0`. The starter takes the standard deviation of the frequency
averaged over non-overlapping blocks of `m` intervals.

**Acceptance** (`tests/test_allan.py`, run by `ctest --test-dir build/debug -R ch38/e4`), with one
time error per 0.5 s, as the monitor of Chapter 38 gives:
- An offset of 300 ps with a frequency 0.1 ppb fast has an Allan deviation of 0 at every tau, and
  `adev` reports `N - 2m` terms.
- A frequency that drifts linearly by D per second gives `D tau / sqrt(2)` at every tau.
- White phase noise of 26 ps gives `sqrt(3) * 26 ps / tau` within 5%, a slope of -1.
- White frequency noise gives `sigma_y / sqrt(m)` within 8%, a slope of -1/2.
- `m` must be a positive integer with at least `2m + 1` samples, and `tau0` positive.

**Then, by hand.**
1. What did the starter give for the linear drift, and why does its answer depend on the length of
   the record? Why did it get white phase noise wrong by a factor of 0.82?
2. A block of Chapter 38's monitor with an offset known to 26 ps per 0.5 s interval: what is its
   Allan deviation at 0.5 s and at 8 s? A block whose clock runs 0.1 ppb fast: what is its Allan
   deviation, and which of the monitor's outputs sees it instead?
3. Why the overlapping estimator, when non-overlapping blocks would be simpler?

**Hints.** The second difference `x[i+2m] - 2 x[i+m] + x[i]` over every `i`, with numpy slices.
The expected Allan variance of white phase noise of variance s^2 is `3 s^2 / tau^2`.
