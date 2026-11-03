# Exercise 26.1: notes on the solution

**The three mistakes.**

- *No background.* The starter took the moments of everything in the window. Patient scatter
  rises towards the photopeak from below, so the window holds more counts on its low side and
  the mean moves down: 0.7% on the acceptance spectra, enough to put a crystal's gain 0.7% low
  and its photopeak 3.5 keV off. The solution subtracts a straight line through two bands
  either side of the peak and fits only what is above it.
- *Moments of a truncated Gaussian.* A window of plus or minus two sigma holds 95% of a
  Gaussian, and the standard deviation of what it holds is 0.88 sigma. Each round narrows the
  window to the new, smaller sigma and shrinks it again. A fit of the shape (a parabola to the
  logarithm) has no such bias: the window only chooses the points.
- *Bin positions.* Bin k of 4 codes holds codes 4k to 4k + 3, so its middle is 4k + 1.5, not
  4k. Half a bin is 1 code in about 1,022: 0.15%, the size of the whole calibration's error
  budget for the gain. `tools/calib/energy.py` adds the same `(width - 1) / 2`.

**Weights** (Then, by hand, 1). On 300 spectra (`rng` seed 5, the acceptance generator):

| Photopeak counts | Fit | Mean sigma / true | Center scatter, rms |
|---:|---|---:|---:|
| 300 | Guo, weights from the counts | 1.136 | 0.48% |
| 300 | unweighted | 1.056 | 0.36% |
| 3,000 | Guo, weights from the counts | 1.010 | 0.12% |
| 3,000 | unweighted | 0.983 | 0.13% |

At 3,000 counts both are within 2% of sigma, and Guo's weights remove the unweighted fit's
pull from the tails, where the logarithm of a few counts is very noisy. At 300 counts the
weights themselves are noisy counts, and the fit follows the bins that fluctuated up: sigma
comes out 14% wide. Guo's paper proposes iterating with the fitted curve's values as the weights
for exactly this case (verify: section "iterative procedure" of the paper before you cite it).
The center, which is what a gain needs, is unbiased in every case. This is why the procedure asks
for 500 photopeak counts and checks sigma only against a wide band (2 to 10% of the center).

**Bands** (2). On the clean spectrum of 50,000 counts, bands just outside the window (2 to
2.5 sigma) gave sigma 11.5% too small: at 2 sigma the Gaussian is still at 13% of its height,
so the "background" took away the peak's own tails and the rest looked narrower. At 3 to 3.5
sigma the Gaussian is at 1% and 0.2%, and sigma came out within 3%. The price is a background
line over a wider span, which matters only where the background curves.

**The summed spectrum** (3). Through the SiPM's saturation (E_sat 1500 keV) a crystal's 12%
FWHM at 511 keV becomes 10.1% in codes (the slope of the response there, 0.711, times 511 /
433). A gain spread of 10% rms adds 23.5% FWHM in quadrature: about 26% expected. The
measurement's fit gave 23.0% before calibration and 12.0% after (`measurements/ch26`): the
summed peak is not a Gaussian, and a fit of its top plus or minus two sigma reads it narrower.
Calibrated, the sum is as wide as one crystal: the 1.1 keV rms spread of the calibrated
photopeaks adds nothing visible.
