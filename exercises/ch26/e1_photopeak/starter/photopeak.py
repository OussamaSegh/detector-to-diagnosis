# SPDX-License-Identifier: MIT
"""Exercise 26.1: one crystal's photopeak, and the gain it gives.

A spectrum is a histogram of the board's energy codes, `width` codes per bin: bin k holds the
codes k * width to (k + 1) * width - 1. The photopeak is a Gaussian on a background that, over the
width of the peak, is close to a straight line (scatter and the Compton continuum below, pile-up
above). fit() finds its centre and sigma in bins; to_code() turns a bin position into a code;
gain() turns the photopeak's code into the crystal's gain for a linear detector.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np

ENERGY_LSB_KEV = 0.5
PEAK_KEV = 511.0


def fit(h, lo, hi, smooth=9, rounds=3):
    """(centre, sigma, ok) of the photopeak of spectrum h, in bins, searched between bins lo and
    hi."""
    h = np.asarray(h, dtype=float)
    sm = np.convolve(h, np.ones(smooth) / smooth, mode="same")
    centre = lo + float(np.argmax(sm[lo:hi]))
    sigma = 0.06 * centre
    x = np.arange(h.size, dtype=float)
    for _ in range(rounds):
        w_lo = int(np.clip(round(centre - 2 * sigma), 1, h.size - 2))
        w_hi = int(np.clip(round(centre + 2 * sigma), 1, h.size - 2))
        inside = slice(w_lo, w_hi + 1)
        y = h[inside]
        # The mean and the standard deviation of the counts in the window.
        centre = float((x[inside] * y).sum() / y.sum())
        sigma = float(np.sqrt(((x[inside] - centre) ** 2 * y).sum() / y.sum()))
    return centre, sigma, True


def to_code(position, width):
    """The code at a position in bins."""
    return position * width


def gain(peak_code):
    """A linear detector's gain: the photopeak at peak_code instead of 511 / 0.5 = 1022."""
    return peak_code * ENERGY_LSB_KEV / PEAK_KEV


def resolution(centre, sigma):
    """FWHM in % of the centre."""
    return 100.0 * 2.3548 * sigma / centre
