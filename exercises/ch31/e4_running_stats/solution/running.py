# SPDX-License-Identifier: MIT
"""Exercise 31.4, a solution: the mean and spread of each crystal's values over a run read in
chunks, in one pass and in memory independent of the run's length.

Each chunk gives, per crystal, its count, its mean and M2, the sum of squared deviations from its
own mean, computed in two passes over the chunk's values. Two summaries merge exactly (Chan,
Golub and LeVeque):

    n = na + nb,  d = mean_b - mean_a,
    mean = mean_a + d nb / n,  M2 = M2_a + M2_b + d^2 na nb / n.

Only differences of close values are ever summed and squared, so a large common offset (time
stamps of 10^15 ps, an hour into a run) costs no digits.
"""
import numpy as np


class RunningStats:
    """Per-crystal count, mean and variance of values given chunk by chunk."""

    def __init__(self, crystals):
        self.n = np.zeros(crystals, dtype=np.int64)
        self.origin = np.zeros(crystals)  # each crystal's first value: everything is kept from it
        self._mean = np.zeros(crystals)   # the mean, less the origin
        self.m2 = np.zeros(crystals)

    @property
    def mean(self):
        return self.origin + self._mean

    def add(self, crystal, values):
        """Adds one chunk: values[k] belongs to crystal[k]."""
        crystal = np.asarray(crystal, dtype=np.int64)
        values = np.asarray(values, dtype=np.float64)
        if crystal.shape != values.shape:
            raise ValueError("crystal and values must have the same shape")
        if crystal.size == 0:
            return
        if crystal.min() < 0 or crystal.max() >= self.n.size:
            raise IndexError(f"a crystal outside 0 to {self.n.size - 1}")
        k = self.n.size
        # Work with each value less its crystal's origin, the first value it ever had: a sum of a
        # thousand time stamps of 3.6e15 ps, or a mean stored at that scale, has lost the digits
        # a spread of 50 ps needs; a difference of two close values is exact.
        seen, first = np.unique(crystal, return_index=True)
        new = self.n[seen] == 0
        self.origin[seen[new]] = values[first[new]]
        x = values - self.origin[crystal]
        nb = np.bincount(crystal, minlength=k)
        with np.errstate(invalid="ignore", divide="ignore"):
            mb = np.where(nb > 0, np.bincount(crystal, x, minlength=k) / nb, 0.0)
        m2b = np.bincount(crystal, (x - mb[crystal]) ** 2, minlength=k)
        n = self.n + nb
        d = mb - self._mean
        with np.errstate(invalid="ignore", divide="ignore"):
            frac = np.where(n > 0, nb / n, 0.0)
        self.m2 = self.m2 + m2b + d * d * self.n * frac
        self._mean = self._mean + d * frac
        self.n = n

    def variance(self):
        """The sample variance (n - 1) of each crystal; NaN for fewer than two values."""
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(self.n > 1, self.m2 / (self.n - 1), np.nan)
