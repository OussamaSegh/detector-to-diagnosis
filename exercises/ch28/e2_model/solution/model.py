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


# [snippet:model]
def reconstruct(y, projector, mult, add, iterations):
    """MLEM with the corrections in the model. Returns the image and the log-likelihood after
    each iteration. y stays the measured counts: it is never divided, subtracted or clipped."""
    y = np.asarray(y, dtype=np.float64)
    mult = np.broadcast_to(np.asarray(mult, dtype=np.float64), y.shape)
    add = np.broadcast_to(np.asarray(add, dtype=np.float64), y.shape)
    sens = projector.back(mult)                 # the bins that are not measured count for 0
    x = np.where(sens > 0, 1.0, 0.0)
    history = []
    for _ in range(iterations):
        ybar = mult * projector.forward(x) + add
        ratio = np.where(ybar > 0, y / np.where(ybar > 0, ybar, 1.0), 0.0)
        x = np.where(sens > 0, x * projector.back(mult * ratio) / np.where(sens > 0, sens, 1.0),
                     0.0)
        history.append(log_likelihood(y, mult * projector.forward(x) + add))
    return x, history
# [/snippet:model]
