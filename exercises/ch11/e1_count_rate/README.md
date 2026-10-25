# Exercise 11.1 (M): Count-rate curves and the NECR peak

**Goal.** Measure a NEMA-style count-rate curve with MiniDAQ's simulator: trues,
scatters and randoms against activity, the scatter fraction and the noise-equivalent
count rate NECR = T² / (T + S + kR), and find the activity at which the NECR peaks, with
and without front-end dead time. This is the plan's "run a count-rate sweep and plot NECR
against activity".

**Time.** 3 hours.

**Starter.** `starter/count_rate.cpp` builds and runs, but its NECR is not squared, it
sorts the singles before the front end has seen them (so dead time changes nothing),
counts every pair from one decay as a true (scattered or not), and reports the best
sample as the peak instead of interpolating. One test, the linear and quadratic growth of
trues and randoms, already passes: its bugs do not change that.

**Acceptance** (`tests/test_count_rate.cpp`):
- NECR and scatter fraction by hand: T = 100, S = 50, R = 25 gives 57.1 for k = 1 and 50
  for k = 2.
- The peak of A·exp(−A/100), sampled at 30, 60, 120 and 240, is found within 6 of 100
  (the nearest sample is 120); a curve symmetric in ln A gives its middle exactly; a curve
  whose highest point is at an end gives NaN.
- The scatter fraction of the NEMA-style phantom at 20 MBq is between 0.30 and 0.40.
- Without dead time, doubling the activity from 50 to 100 MBq multiplies the trues by
  1.7 to 2.3 and the randoms by 3.0 to 5.2.
- A 1 µs non-paralyzable dead time per block, with pile-up, keeps less than 70% of the
  trues at 100 MBq, and brings the NECR (k = 1) peak of a 20 to 400 MBq sweep to between
  40 and 200 MBq.

The tests simulate half a million decays per point and take about half a minute in a
Debug build.

**Then, by hand.** Sweep 5 to 1000 MBq with more decays per point (the chapter's
`measurements/ch11/countrate.py` does it with `minidaq_sim`) and plot the trues, scatters,
randoms and NECR for k = 1 and k = 2, with and without dead time. In `NOTES.md`: where does
each curve peak, why does the curve without dead time still peak, and which of the three
rates limits the NECR at the peak?

**Hints.** If T grew exactly as A and R as A², what would T²/(T + S + kR) do as A grows
without bound? So what must happen to T for the curve to fall? For the peak: a parabola
through three points has its vertex where the derivative is zero; write it in x = ln A, in
which a sweep on a 1, 2, 5 grid is close to evenly spaced.
