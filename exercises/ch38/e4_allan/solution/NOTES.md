# Exercise 38.4: notes on the solution

## 1. The starter's standard deviation

For a frequency that drifts linearly, the starter's standard deviation of the averaged frequency
is the spread of a straight line over the whole record: 8,164 times the Allan deviation at
tau = 0.5 s on 20,000 samples, and it doubles if the record is twice as long. A classical standard
deviation measures how far the frequency is from its mean over the record, and a drifting
frequency has no mean to be close to: the longer you look, the larger it gets. The Allan variance
compares each average with the next one only, so it converges for drift and for the slower noises
where the classical one diverges, which is why it was introduced.

For white phase noise, the starter's averaged frequency over one block is
`(x[end] - x[start]) / tau`, of variance `2 s^2 / tau^2`; the Allan variance is half the mean square
of a second difference, `6 s^2 / 2 tau^2 = 3 s^2 / tau^2`. The ratio of the deviations is
`sqrt(2/3) = 0.82`.

## 2. The monitor's numbers

An offset known to 26 ps per 0.5 s behaves as white phase noise of 26 ps: an Allan deviation of
`sqrt(3) * 26 ps / 0.5 s = 9.0e-11` at 0.5 s and `5.6e-12` at 8 s, falling as 1/tau. A clock 0.1
ppb fast has an Allan deviation of exactly 0: a constant frequency is a straight line in the time
error, and a second difference removes it. The monitor sees it through its offset, which grows by
100 ps per second until it passes the alarm threshold, 3.5 s into the run in
`measurements/ch38/time_base.txt`. The Allan deviation characterizes the noise of a time base, and
tells which averaging time gives the best estimate (the minimum of the curve); it is not a
detector of a clock that is wrong in a constant way, which is what an alarm is for.

The same arithmetic says when wander would matter: white phase noise of 26 ps per interval at
0.5 s equals a frequency stability of 1e-10 at tau = 0.45 s. A wander that the monitor could
separate from its own statistical noise must stand above the 1/tau line at the taus it averages
over.

## 3. Overlapping

With N samples, non-overlapping blocks give about N/m - 2 second differences at tau = m tau0, the
overlapping estimator N - 2m. They are not independent, but they average down the noise of the
estimate considerably at large m, where non-overlapping blocks leave only a handful of terms. The
expected value is the same; the confidence interval is narrower for the same data, which for a
measurement that costs hours of acquisition is the reason.
