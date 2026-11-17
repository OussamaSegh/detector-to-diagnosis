# SPDX-License-Identifier: MIT
"""Exercise 31.4: the mean and spread of each crystal's values over a run read in chunks, in one
pass and in memory independent of the run's length.

This starter runs and gives plausible numbers. TODO: make the tests pass.
"""
import numpy as np


class RunningStats:
    """Per-crystal count, mean and variance of values given chunk by chunk."""

    def __init__(self, crystals):
        self.n = np.zeros(crystals, dtype=np.int64)
        self.mean = np.zeros(crystals)
        self.sum2 = np.zeros(crystals)
        self.chunks = 0

    def add(self, crystal, values):
        """Adds one chunk: values[k] belongs to crystal[k]."""
        crystal = np.asarray(crystal, dtype=np.int64)
        values = np.asarray(values, dtype=np.float64)
        k = self.n.size
        nb = np.bincount(crystal, minlength=k)
        mb = np.bincount(crystal, values, minlength=k) / np.maximum(nb, 1)
        # The running mean is the mean of the chunks' means.
        self.mean = (self.mean * self.chunks + mb) / (self.chunks + 1)
        self.sum2 += np.bincount(crystal, values * values, minlength=k)
        self.n += nb
        self.chunks += 1

    def variance(self):
        """The sample variance (n - 1) of each crystal."""
        n = np.maximum(self.n, 2)
        return (self.sum2 - n * self.mean**2) / (n - 1)
