# Exercise 26.1 (M): Find a crystal's photopeak

**Goal.** Fit the 511 keV photopeak of one crystal's energy spectrum as a Gaussian on a
straight background, get its centre and width right to a fraction of a percent, and turn
the centre into the crystal's gain. This is the fit `tools/calib/energy.py` runs on all
18,432 crystals at once.

**Time.** 75 minutes.

**Starter.** `starter/photopeak.py` runs and gives plausible numbers. `fit` takes the mean
and the standard deviation of the counts in a window of plus or minus two sigma around the
highest bin; `to_code` multiplies a bin position by the bin width. `gain` and `resolution`
are correct.

**Acceptance** (`tests/test_photopeak.py`, synthetic spectra of 4 codes per bin):
- `to_code` puts bin 0 of 4 codes at code 1.5, the middle of codes 0 to 3.
- Without background, 50,000 photopeak counts: the centre within 0.1% and sigma within 3%.
- With patient scatter under the peak (a ramp of 0.8 times the peak's counts): the centres
  of 40 spectra of 3,000 counts are unbiased to 0.2%, none is off by more than 0.8%, and
  sigma is unbiased to 6%.
- The gains of 30 crystals of 2,000 counts are within 0.3% rms of the truth.

**Then, by hand.**
1. Fit a parabola to the logarithm of the counts without weights (Caruana's method). On 300
   spectra of 300 counts each, what happens to the mean of sigma? Why do Guo's weights
   (each point weighted by its counts squared) fix it?
2. Where should the background bands be? Try bands just outside the window (2 to 2.5 sigma)
   and at 3 to 3.5 sigma on the clean spectrum. What does each do to sigma, and why?
3. The summed spectrum of all crystals of an uncalibrated detector with a 10% gain spread
   and a 5% sigma per crystal: what FWHM do you expect, and what did `measurements/ch26`
   find? Answer in `NOTES.md`.

**Hints.** A Gaussian is a parabola in the logarithm: ln y = A + B u + C u^2 gives centre
-B / 2C and sigma sqrt(-1 / 2C). Subtract the background before you take the logarithm.
The window's moments of a Gaussian are not its sigma: a window of plus or minus two sigma
holds 95% of it and its standard deviation is 0.88 sigma.
