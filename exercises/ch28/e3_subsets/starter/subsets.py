# SPDX-License-Identifier: MIT
"""Exercise 28.3: OSEM, ordered subsets of the views.

The model is that of Exercise 28.2: y is Poisson with mean mult * (A x) + add. `projector` has
forward(x, views) and back(y, views) for any list of views.
"""
import numpy as np


def subsets(views, count):
    """count subsets that together hold every view once: consecutive blocks of views."""
    return [list(b) for b in np.array_split(np.arange(views), count)]


def osem(y, projector, mult, add, iterations, count, x0=None):
    """count updates per iteration, one per subset S. The sensitivity is that of all the views
    divided by count, computed once."""
    y = np.asarray(y, dtype=np.float64)
    mult = np.broadcast_to(np.asarray(mult, dtype=np.float64), y.shape)
    add = np.broadcast_to(np.asarray(add, dtype=np.float64), y.shape)
    groups = subsets(y.shape[0], count)
    sens = projector.back(mult) / count
    x = np.ones((projector.n, projector.n)) if x0 is None else np.array(x0, dtype=np.float64)
    for _ in range(iterations):
        for g in groups:
            ybar = mult[g] * projector.forward(x, g) + add[g]
            ratio = np.where(ybar > 0, y[g] / np.where(ybar > 0, ybar, 1.0), 0.0)
            x = np.where(sens > 0,
                         x * projector.back(mult[g] * ratio, g) / np.where(sens > 0, sens, 1.0),
                         0.0)
    return x
