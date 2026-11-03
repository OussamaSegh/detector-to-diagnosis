# SPDX-License-Identifier: MIT
"""Exercise 31.2: a timing peak fitted by Poisson maximum likelihood, with uncertainties.

numpy only: the model is a Gaussian on a flat background, integrated over each bin; the fit is
Fisher scoring; the errors are the square roots of the diagonal of the inverse Fisher matrix."""
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
        h = 1e-5 * max(abs(p[i]), 1.0)  # at least 1e-5 of a unit: a mean near 0 needs it
        up, down = p.copy(), p.copy()
        up[i] += h
        down[i] -= h
        jac[:, i] = (expected(edges, up) - expected(edges, down)) / (2 * h)
    return jac


def _deviance(n, mu):
    safe = np.where(n > 0, n, 1.0)
    return float(2.0 * np.sum(mu - n + np.where(n > 0, n * np.log(safe / mu), 0.0)))


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
    low = np.array([0.0, edges[0], width / 10, 0.0])
    high = np.array([np.inf, edges[-1], edges[-1] - edges[0], np.inf])
    mu = expected(edges, p)
    d = _deviance(n, mu)
    for _ in range(100):
        jac = _jacobian(edges, p)
        score = jac.T @ (n / mu - 1.0)
        info = jac.T @ (jac / mu[:, None])
        free = ~(((p <= low) & (score < 0)) | ((p >= high) & (score > 0)))
        step = np.zeros_like(p)
        step[free] = np.linalg.solve(info[np.ix_(free, free)], score[free])
        if 2.0 * float(score @ step) < 1e-9:
            break
        t = 1.0
        while t > 1e-10:
            q = np.clip(p + t * step, low, high)
            mu_q = expected(edges, q)
            if np.all(mu_q > 0) and _deviance(n, mu_q) <= d:
                p, mu, d = q, mu_q, _deviance(n, mu_q)
                break
            t *= 0.5
        else:
            raise RuntimeError("the fit cannot lower the deviance")
    else:
        raise RuntimeError("the fit did not converge")
    jac = _jacobian(edges, p)
    cov = np.linalg.inv(jac.T @ (jac / mu[:, None]))
    err = np.sqrt(np.diag(cov))
    out = {name: (float(p[i]), float(err[i])) for i, name in enumerate(NAMES)}
    k = 2.0 * math.sqrt(2.0 * math.log(2.0))
    out["fwhm"] = (k * float(p[2]), k * float(err[2]))
    return out
