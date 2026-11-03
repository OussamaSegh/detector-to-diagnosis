# SPDX-License-Identifier: MIT
"""Exercise 28.2: the corrections in the model, not in the data.

The counts y of each bin are Poisson with mean  ybar = mult * (A x) + add:  mult holds the
normalization, attenuation and live fraction of the bin (0 where the bin is not measured, in a
gap), add its randoms and scatter. `projector` has forward(x) = A x and back(y) = A^T y.
"""
import numpy as np


def log_likelihood(y, ybar):
    """sum(y log ybar - ybar) over the bins with ybar > 0; -inf if a bin with ybar = 0 has
    counts."""
    pos = ybar > 0
    if np.any(y[~pos] > 0):
        return -np.inf
    return float((y[pos] * np.log(ybar[pos]) - ybar[pos]).sum())


def reconstruct(y, projector, mult, add, iterations):
    """Corrects the data first, (y - add) / mult with negatives set to 0, then runs plain MLEM on
    the corrected sinogram. Returns the image and the log-likelihood after each iteration."""
    y = np.asarray(y, dtype=np.float64)
    mult = np.broadcast_to(np.asarray(mult, dtype=np.float64), y.shape)
    add = np.broadcast_to(np.asarray(add, dtype=np.float64), y.shape)
    corrected = np.where(mult > 0, np.maximum(y - add, 0.0) / np.where(mult > 0, mult, 1.0), 0.0)
    sens = projector.back(np.ones_like(y))
    x = np.ones((projector.n, projector.n))
    history = []
    for _ in range(iterations):
        ybar = projector.forward(x)
        ratio = np.where(ybar > 0, corrected / np.where(ybar > 0, ybar, 1.0), 0.0)
        x = x * projector.back(ratio) / sens
        history.append(log_likelihood(y, mult * projector.forward(x) + add))
    return x, history
