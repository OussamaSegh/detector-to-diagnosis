# SPDX-License-Identifier: MIT
"""MLEM and OSEM for a 2D sinogram (Chapter 28), numpy only.

The model: the counts y of each bin are Poisson with mean  ybar = m * (A x) + b,  where x is the
image, A the projector (line integrals), m the bin's multiplicative factors (normalization times
attenuation times live fraction, Chapter 27) and b its additive ones (randoms, and scatter times
the normalization). The corrections are in the model, not applied to the data: y stays Poisson,
which is what the algorithm's statistics assume, and no bin is ever negative.
"""
import numpy as np


def log_likelihood(y, ybar):
    """The Poisson log-likelihood sum(y log ybar - ybar), without the constant -log(y!). Bins with
    ybar = 0 must have y = 0 (otherwise the model is impossible) and contribute nothing."""
    y = np.asarray(y, dtype=np.float64)
    ybar = np.asarray(ybar, dtype=np.float64)
    pos = ybar > 0
    if np.any(y[~pos] > 0):
        return -np.inf
    return float((y[pos] * np.log(ybar[pos]) - ybar[pos]).sum())


def subsets(views, count):
    """The views of each subset: every count-th view, so that each subset covers all angles."""
    if not 1 <= count <= views:
        raise ValueError(f"{count} subsets of {views} views")
    return [list(range(k, views, count)) for k in range(count)]


# [snippet:osem]
def osem(y, projector, mult, add, iterations, n_subsets=1, x0=None, callback=None):
    """OSEM: one EM update per subset of views, n_subsets updates per iteration; n_subsets = 1 is
    MLEM. Each update multiplies the image by the backprojected ratio of measured to expected
    counts, divided by the subset's sensitivity (the backprojection of m):

        x <- x / (A_S^T m_S) * A_S^T ( m_S * y_S / (m_S A_S x + b_S) )

    The update keeps x >= 0, and for MLEM it never decreases the likelihood. callback(it, x), if
    given, is called after each full iteration."""
    y = np.asarray(y, dtype=np.float64)
    mult = np.broadcast_to(np.asarray(mult, dtype=np.float64), y.shape)
    add = np.broadcast_to(np.asarray(add, dtype=np.float64), y.shape)
    n = projector.n
    x = np.ones((n, n)) if x0 is None else np.array(x0, dtype=np.float64)
    groups = subsets(y.shape[0], n_subsets)
    sens = [projector.back(mult[g], g) for g in groups]
    for it in range(1, iterations + 1):
        for g, s in zip(groups, sens):
            ybar = mult[g] * projector.forward(x, g) + add[g]
            ratio = np.where(ybar > 0, y[g] / np.where(ybar > 0, ybar, 1.0), 0.0)
            x = np.where(s > 0, x * projector.back(mult[g] * ratio, g) / np.where(s > 0, s, 1.0),
                         0.0)
        if callback is not None:
            callback(it, x)
    return x
# [/snippet:osem]


def expected(x, projector, mult, add):
    """The model's mean counts for image x."""
    return np.asarray(mult) * projector.forward(x) + np.asarray(add)
