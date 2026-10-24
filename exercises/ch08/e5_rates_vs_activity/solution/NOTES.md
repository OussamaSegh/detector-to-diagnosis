# Exercise 8.5: notes on the solution

On the book's machine (seeds 1 to 4, 0.2 s per activity, 10 ns window, 100 to 1000 keV):

| Activity | Trues /s | Scatters /s | Randoms /s | Trues per decay | Randoms fraction |
|---|---|---|---|---|---|
| 1 MBq | 20,480 | 37,860 | 1,140 | 0.0205 | 1.9% |
| 2 MBq | 39,420 | 74,500 | 4,395 | 0.0197 | 3.7% |
| 4 MBq | 79,040 | 145,200 | 17,050 | 0.0198 | 7.1% |
| 8 MBq | 154,200 | 283,300 | 66,600 | 0.0193 | 13.2% |

Fitted exponents: trues 0.974, scatters 0.967, randoms 1.956.

**Why the sensitivity falls.** Every decay is simulated the same way, but the counter
discards any window with three or more singles. At 8 MBq the scanner sees about 3.6 M
singles per second, so a 10 ns window opened by a true single contains an unrelated
single with probability of a few percent, and the true pair inside it is lost as a
multiple. That is why the trues exponent is slightly below 1: a count loss that grows
with activity. Chapter 11 treats it with dead time and pile-up.

**Randoms equal trues.** R / T is 0.43 at 8 MBq and grows about linearly with activity
(exponent 1.956 - 0.974 = 0.98), so R = T near 19 MBq for this window. Randoms are
proportional to the window width, trues are not (as long as the window keeps them), so
halving the window to 5 ns would move that point to about 38 MBq. At high activity, the
narrowest window that keeps the trues pays for itself; the timing resolution decides
how narrow that is (Exercise 8.1).

**What the starter's fit did.** A straight line through raw values gives a slope in
counts per second per becquerel, not an exponent; the randoms curve is not a straight
line, and no single slope describes it.
