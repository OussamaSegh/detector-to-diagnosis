# Exercise 8.5 (M, extra): Trues, scatters and randoms versus activity

**Goal.** Use MiniDAQ's detector simulator and its ground truth to measure how the rates
of trues, scatters and randoms grow with activity, fit a power law to each, and confirm
the Check yourself answer with numbers: trues and scatters are linear in activity,
randoms quadratic.

**Time.** 2 hours.

**Starter.** `starter/rates.cpp`: `sweep` is a TODO; `fit_power_law` fits a straight line
to the raw values, which is not a power law.

**Acceptance** (`tests/test_rates.cpp`):
- `sweep` over 1, 2, 4 and 8 MBq (0.2 s each, a uniform cylinder in the water phantom of
  `minidaq_sim`, a 10 ns window, 100 to 1000 keV) returns one `RatePoint` per activity,
  with rates per second.
- `fit_power_law` recovers the exponent and prefactor of exact power laws to 1e-9.
- The fitted exponent is within 0.05 of 1 for trues and for scatters, and within 0.1
  of 2 for randoms.
- Trues per decay (the sensitivity) is 2 to 10% lower at 8 MBq than at 1 MBq, and the
  randoms fraction R / (T + S + R) rises with every step.

Then, in `NOTES.md`: why does the sensitivity fall at all, when every decay is
simulated the same way? At which activity would randoms equal trues, if you extrapolate
the two power laws? What does that say about the window width at high activity?

**Hints.** A power law y = a x^k is a straight line in log-log coordinates. The
simulator's `generate_until` and `count_coincidences` do the heavy lifting; build a fresh
simulator for each activity, with its own seed.
