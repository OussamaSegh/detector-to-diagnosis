# SPDX-License-Identifier: MIT
"""Exercise 31.2: a timing peak fitted by Poisson maximum likelihood, with uncertainties.

The starter fits by least squares with each bin weighted by its observed count (what
scipy.optimize.curve_fit does with sigma=sqrt(counts)), by Gauss-Newton."""
import math

import numpy as np

NAMES = ("area", "mean", "sigma", "background")
_erf = np.vectorize(math.erf)


def expected(edges, p):
    """Counts per bin of a Gaussian of area p[0], mean p[1], sigma p[2] on p[3] counts per ps."""
    lo, hi = edges[:-1], edges[1:]
    s = p[2] * math.sqrt(2.0)
    return 0.5 * p[0] * (_erf((hi - p[1]) / s) - _erf((lo - p[1]) / s)) + p[3] * (hi - lo)


def _jacobian(edges, p):
    jac = np.empty((edges.size - 1, p.size))
    for i in range(p.size):
        h = 1e-6 * max(abs(p[i]), 1e-3)
        up, down = p.copy(), p.copy()
        up[i] += h
        down[i] -= h
        jac[:, i] = (expected(edges, up) - expected(edges, down)) / (2 * h)
    return jac


def fit_timing(counts, edges):
    """{name: (value, standard error)} for area, mean, sigma, background, and fwhm."""
    n = np.asarray(counts, dtype=float)
    edges = np.asarray(edges, dtype=float)
    if n.sum() < 50:
        raise ValueError("too few counts for a fit")
    c = 0.5 * (edges[1:] + edges[:-1])
    width = float(np.mean(np.diff(edges)))
    floor = float(np.median(np.concatenate([n[:5], n[-5:]])))
    above = np.clip(n - floor, 0, None)
    mean0 = float(np.sum(c * above) / max(above.sum(), 1.0))
    sigma0 = math.sqrt(max(float(np.sum((c - mean0) ** 2 * above) / max(above.sum(), 1.0)),
                           width**2))
    p = np.array([max(above.sum(), 1.0), mean0, sigma0, max(floor, 0.5) / width])
    w = 1.0 / np.maximum(n, 1.0)  # weights from the observed counts
    for _ in range(100):
        r = n - expected(edges, p)
        jac = _jacobian(edges, p)
        step = np.linalg.lstsq(jac.T @ (jac * w[:, None]), jac.T @ (w * r), rcond=None)[0]
        p = p + step
        p[2] = abs(p[2])
        p[3] = max(p[3], 1e-6)  # a background is never negative
        if np.all(np.abs(step) < 1e-8 * np.maximum(np.abs(p), 1.0)):
            break
    jac = _jacobian(edges, p)
    cov = np.linalg.inv(jac.T @ (jac * w[:, None]))
    err = np.sqrt(np.diag(cov))
    out = {name: (float(p[i]), float(err[i])) for i, name in enumerate(NAMES)}
    k = 2.0 * math.sqrt(2.0 * math.log(2.0))
    out["fwhm"] = (k * float(p[2]), k * float(err[2]))
    return out
