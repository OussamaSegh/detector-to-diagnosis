# SPDX-License-Identifier: MIT
"""Exercise 26.1: one crystal's photopeak, and the gain it gives.

A spectrum is a histogram of the board's energy codes, `width` codes per bin: bin k holds the
codes k * width to (k + 1) * width - 1. The photopeak is a Gaussian on a background that, over the
width of the peak, is close to a straight line (scatter and the Compton continuum below, pile-up
above). fit() finds its center and sigma in bins; to_code() turns a bin position into a code;
gain() turns the photopeak's code into the crystal's gain for a linear detector.
"""
import numpy as np

ENERGY_LSB_KEV = 0.5
PEAK_KEV = 511.0


# [snippet:fit]
def fit(h, lo, hi, smooth=9, rounds=3):
    """(center, sigma, ok) of the photopeak of spectrum h, in bins, searched between bins lo and
    hi. A Gaussian on a straight background, by Guo's weighted fit of a parabola to the logarithm
    of the counts above the background."""
    h = np.asarray(h, dtype=float)
    sm = np.convolve(h, np.ones(smooth) / smooth, mode="same")
    center = lo + float(np.argmax(sm[lo:hi]))
    sigma = 0.06 * center  # a typical LYSO resolution, as a first guess
    x = np.arange(h.size, dtype=float)
    for _ in range(rounds):
        w_lo = int(np.clip(round(center - 2 * sigma), 1, h.size - 2))
        w_hi = int(np.clip(round(center + 2 * sigma), 1, h.size - 2))
        # The background: the line through the mean counts of two bands, 3 to 3.5 sigma from
        # the center, where the Gaussian has fallen to 1% of its height. Bands just outside the
        # window would still hold the peak's tails and make it look narrower.
        b_lo = [int(round(center - 3.5 * sigma)), int(round(center - 3 * sigma)) + 1]
        b_hi = [int(round(center + 3 * sigma)), int(round(center + 3.5 * sigma)) + 1]
        if b_lo[0] < 0 or b_hi[1] > h.size or b_lo[1] - b_lo[0] < 1 or b_hi[1] - b_hi[0] < 1:
            return center, sigma, False
        xl, yl = (b_lo[0] + b_lo[1] - 1) / 2.0, h[b_lo[0]:b_lo[1]].mean()
        xr, yr = (b_hi[0] + b_hi[1] - 1) / 2.0, h[b_hi[0]:b_hi[1]].mean()
        background = yl + (yr - yl) / (xr - xl) * (x - xl)
        inside = slice(w_lo, w_hi + 1)
        y = np.maximum(h[inside] - background[inside], 0.0)
        u = x[inside] - center
        keep = y > 0
        if keep.sum() < 5:
            return center, sigma, False
        # Guo: minimize sum y^2 (ln y - (A + B u + C u^2))^2. The weights y^2 undo what the
        # logarithm does to the noise of the small counts in the tails.
        A = np.stack([np.ones(keep.sum()), u[keep], u[keep] ** 2], 1)
        w = y[keep]
        coef, *_ = np.linalg.lstsq(A * w[:, None], np.log(y[keep]) * w, rcond=None)
        _, b, c = coef
        if c >= 0:
            return center, sigma, False
        center, sigma = center - b / (2 * c), float(np.sqrt(-1 / (2 * c)))
    return center, sigma, w_lo - 1 < center < w_hi + 1
# [/snippet:fit]


def to_code(position, width):
    """The code at a position in bins: bin k is centered on code k * width + (width - 1) / 2."""
    return position * width + (width - 1) / 2.0


def gain(peak_code):
    """A linear detector's gain: the photopeak at peak_code instead of 511 / 0.5 = 1022."""
    return peak_code * ENERGY_LSB_KEV / PEAK_KEV


def resolution(center, sigma):
    """FWHM in % of the center."""
    return 100.0 * 2.3548 * sigma / center
