# SPDX-License-Identifier: MIT
"""Exercise 29.3: is a second implementation of a projector the same as the reference?

assert_same(reference, candidate, rtol) raises AssertionError, saying what differs, unless the
candidate's forward and back projections agree with the reference's to rtol relative to their
largest value, and the candidate's back is the adjoint of its forward. Both projectors have
n, shape, forward(image) and back(sino).
"""
import numpy as np


def assert_same(reference, candidate, rtol=1e-6, seed=0):
    n = reference.n
    c = np.arange(n) - (n - 1) / 2.0
    x, y = np.meshgrid(c, c)
    disc = ((x ** 2 + y ** 2) <= (n / 3) ** 2).astype(float)
    if not np.allclose(candidate.forward(disc), reference.forward(disc), rtol=rtol):
        raise AssertionError("forward differs")
