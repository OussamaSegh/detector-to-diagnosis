# Exercise 28.2: notes on the solution

**The two mistakes.**

- *Corrected data is not Poisson.* `(y - add) / mult` has the right mean only while it is
  allowed to be negative. Set the negative bins to 0 and the mean goes up wherever the trues are
  few compared with the randoms, which in a short frame is nearly everywhere. MLEM also takes the
  data as Poisson counts, which the corrected values are not. The solution leaves `y` as
  measured and puts the factors in the expected counts:
  `ybar = mult * forward(x) + add`, the update `x * back(mult * y / ybar) / back(mult)`.
- *An unmeasured bin is not a bin that measured zero.* The starter set the gaps to 0 and kept
  them in the update with the full sensitivity. MLEM then looked for an image whose projection
  is 0 along every line through a gap, which no smooth image has: the disc came out in stripes,
  a standard deviation of 1.08 against the solution's 0.023, and its likelihood went down in
  some iterations. With `mult = 0` in the expected counts, the backprojected ratio and the
  sensitivity, a gap's bins take no part in the update.

**The clipped counts** (Then, by hand, 1). Over the 20 realizations, setting the negative bins
to 0 made the corrected sinogram's sum 1.70 times the unclipped one, which has the right mean
(1621 against 1613 for the true projection). After 20 iterations the starter's image held 1.67
times the true activity. It put the excess in the background, 0.065 outside the disc against
0.028 for the solution after 100 iterations, and the disc itself came out 7% low, because the
clipped data has the shape of a pedestal, not of the object. More iterations do not help (0.928
after 100); more counts do, since fewer bins go negative (0.985 with 100 times the counts).

**The gaps** (2). To MLEM a 0 in the data is a measurement: no decay happened along that line.
Every line through the disc in a gap told it so, and it took activity out of the pixels on those
lines and put it on the lines nearby, in stripes that repeat every sixth bin. A real scanner has
gaps between its blocks and crystals that die, and a reconstruction that does not take them out
of the model shows them in every image.

**The background outside the disc** (3). Two things keep it above 0. The first is convergence:
where the randoms dominate a bin, `ybar` is mostly `add`, the ratio moves little, and activity
leaves the empty pixels slowly. On noiseless data the ring outside the disc still held 20% of
the disc's level after 20 iterations and 4.3% after 100. The second is the noise: the image is
constrained to be non-negative, so the fluctuations of the randoms below their mean cannot be
explained by negative activity, while those above it come out as positive activity where there
is none. With noise the ring held 28% after 100 iterations. Neither is a fault of the model: the
first is a slow algorithm (Chapter 28 discusses how many iterations to run), the second the price
of a non-negative estimate, and the mean over the disc stays within 0.7% of the truth. The
starter's 65% comes on top, from the data it was given.
