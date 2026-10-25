# Exercise 11.4 (E): Correcting a measured rate for dead time

**Goal.** Invert the two dead-time models: from the rate a unit recorded back to the rate
that arrived. Handle the paralyzable model's two branches and its maximum, and work out how
much the correction amplifies the uncertainty of the measured rate.

**Time.** 1 hour.

**Starter.** `starter/correction.py` inverts the non-paralyzable model with the wrong sign,
uses a first-order guess for the paralyzable one (and ignores the branch), and claims the
correction does not amplify errors.

**Acceptance** (`tests/test_correction.py`, run by CTest as `ch11/e4_dead_time_correction/...`):
- Round trip on the low branch, both models, from 1,000/s to 900,000/s with τ = 1 µs: the
  corrected rate equals the true rate to nine digits.
- Non-paralyzable by hand: 1 M/s records 500,000/s; nothing corrects a recorded 1 M/s.
- Paralyzable: the rate that records the same as 300,000/s on the high branch is
  2.3646 M/s; the maximum 1/(eτ) corrects to 1/τ, and anything above it is NaN.
- Error amplification (dn/n)/(dm/m): 1.5 (non-paralyzable) and 2.0 (paralyzable) at
  500,000/s, and both agree with a numerical derivative.
- A simulated unit at 500,000/s for 1 s loses a third or more of its events; the corrected
  rate is within 1% of the truth.

**Hints.** n exp(−n τ) = m has no closed form without the Lambert W function. On each side
of n = 1/τ the left-hand side is monotonic, so bisection is safe; Newton's method from n = m
also works on the low side, which is what MiniDAQ's `sim::true_rate` does.

**Afterwards.** Plot the error amplification of both models against nτ from 0 to 0.9. A
system specified to "correct dead time to within 1%" with a 0.5% uncertainty in each measured
rate: up to which nτ does it meet that specification?
